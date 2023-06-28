import math
import os
from typing import Final
from message import Message
import ext4
import argparse


def check_powers(n):
    if n == 0 or n == 1:
        return True
    nums = [3, 5, 7]
    for num in nums:
        if math.log10(n) / math.log10(num) % 1 == 0:
            return True
    return False


class Detect:
    def __init__(self, file_name=None, string=None, log=False):
        self.log = log
        if file_name is None:
            raise FileNotFoundError

        self.check_string = False
        self.is_list = False
        if string is not None:
            self.check_string = True
            self.string = string
            if type(self.string) == list:
                self.is_list = True
                for i in range(len(self.string)):
                    self.string[i] = self.string[i].encode()
            else:
                self.string = self.string.encode()

        self.file_name = file_name
        self.messages = []
        self.file_name = file_name
        self.file = open(self.file_name, "rb")
        self.fd = os.open(self.file_name, os.O_RDONLY)
        self.volume = ext4.Volume(self.file, offset=0)
        self.found = False
        self.techniques = []

        # Info
        self.superblock = self.volume.superblock
        self.block_size = self.volume.block_size
        self.blocks_per_group = getattr(self.superblock, "s_blocks_per_group")
        self.group_descriptors = self.volume.group_descriptors

    def __del__(self):
        if hasattr(self, "file"):
            self.file.close()
            os.close(self.fd)

        if not self.log:
            return

        if self.messages:
            for message in self.messages:
                print(message)
            return

        print("No problems found.")

    def create_incident(self, inode, msg, technique, found=False):
        """
        Creates a message object and store them in the self.messages
        list.
        Params:
            inode - Number of the inode
            msg - Message which the program will output
        """
        if self.found:
            incident = Message(inode=inode, msg=msg, data=self.string)
        else:
            incident = Message(inode=inode, msg=msg)
        self.found = False
        self.messages.append(incident)
        if technique not in self.techniques:
            self.techniques.append(technique)

    def handle_found_data(self, n_inode: int, data: bytes, message: str, type: str):
        if not self.check_string:
            self.create_incident(n_inode, message, type)
            return
        if self.is_list:
            for string in self.string:
                if string in data:
                    self.found = True
                    self.create_incident(n_inode, message, type)
            return
        if self.string in data:
            self.found = True
            self.create_incident(n_inode, message, type)

    def handle_found_multiple_data(self, n_inode: int, first_half: bytes, second_half: bytes, message: str, type: str):
        if not self.check_string:
            self.create_incident(n_inode, message, type)
            return
        if self.is_list:
            for string in self.string:
                if string in first_half or string in second_half:
                    self.found = True
                    self.create_incident(n_inode, message, type)
            return
        if self.string in first_half or self.string in second_half:
            self.found = True
            self.create_incident(n_inode, message, type)

    def check_file_slack(self):
        """
        Checks if there is any data in the file slack of files
        """
        n_inodes = getattr(self.superblock, "s_inodes_count")
        for inode_n in range(n_inodes):
            inode = self.volume.get_inode(inode_n)
            # Check if the inode entry is a file
            if not inode.is_file:
                continue
            size = inode.__len__()
            # Try to obtain the bitmap
            try:
                start_block = inode.open_read().block_map[0].disk_block_idx
            except:
                continue
            n_blocks = inode.open_read().block_map[0].block_count
            end_block = (start_block + n_blocks - 1) * self.block_size
            # Calculate space
            block_used = size % self.block_size
            if block_used == 0:
                continue
            location = end_block + block_used
            size_to_read = self.block_size - block_used
            data = os.pread(self.fd, size_to_read, location)
            if data != b"\x00" * size_to_read:
                self.handle_found_data(inode_n, data, "File slack is not empty.", "file_slack")
                return 1
        return 0

    def check_osd2(self):
        """
        Checks if there is data in the OSD2-field
        Returns:
            Number of incidents where there is data in the OSD2 field
        """
        count = 0
        osd2_offset: Final = 0x7E
        n_inodes = getattr(self.superblock, "s_inodes_count")
        # Loop through all the inodes
        for n_inode in range(n_inodes):
            # Obtain the inode
            inode = self.volume.get_inode(n_inode)
            offset = inode.offset + osd2_offset
            # Obtain the data and make sure it is all 0's
            data = os.pread(self.fd, 2, offset)
            if data != b"\x00\x00":
                count += 1
                self.handle_found_data(n_inode, data, "OSD2 is not empty.", "osd2")
        return count

    def check_superblock_backup(self):
        """
        Checks if the backups are identical
        If not, there is a chance that there is tampered with.
        Returns:
            Number of occurrences where the backup is not identical
        """
        l_offset = 0
        if self.block_size == 1024:
            l_offset = 1
        count = 0
        size_first_half: Final = 90
        second_half_block_nr: Final = 94
        size_second_half: Final = 926

        # Obtain first backup-block, to check if it is the same
        # as the other backup blocks
        first_half_offset = (self.blocks_per_group + l_offset) * self.block_size
        first_half = os.pread(self.fd, size_first_half, first_half_offset)
        # Skip the block number, which is stored in (90,94)
        second_half_offset = first_half_offset + second_half_block_nr
        second_half = os.pread(self.fd, size_second_half, second_half_offset)
        for gd in range(len(self.group_descriptors)):
            # Skip block 0, is checked by e2fsck.
            if not check_powers(gd) or gd == 0:
                continue

            # Obtain data
            block_nr = (gd * self.blocks_per_group) + l_offset
            offset = block_nr * self.block_size
            backup_first_half = os.pread(self.fd, size_first_half, offset)
            second_location = offset + second_half_block_nr
            backup_second_half = os.pread(self.fd, size_second_half, second_location)

            # Check if the backup is the same as the first backup
            if first_half != backup_first_half or second_half != backup_second_half:
                self.handle_found_multiple_data(-1, backup_first_half, backup_second_half, "Superblock copy " + str(gd) + " is not the same.",
                                                "backup_superblock")
                count += 1

        return count

    def check_partition_boot_sector(self):
        """
        Check if the partition boot sector is empty.
        This is not necessary hided data: PBS could be used in xx. However, it is suspicious
        Returns:
            1 if there is data in the PBS, 0 otherwise
        """
        length_pbs: Final = 0x400
        pbs = os.pread(self.fd, length_pbs, 0)
        if pbs != (b"\x00" * length_pbs):
            self.handle_found_data(-1, pbs, "The Partition Boot Sector is not empty.", "partition_boot_sector")
            return 1
        return 0

    def check_reserved_space_inodes(self):
        """
        Check the reserved space in the inodes (0x7A)
        Returns:
            Number of occurrences where the reserved space is not empty
        """
        count = 0
        reserved_space_offset: Final = 0x7A
        len_reserved_space: Final = 2
        n_inodes = getattr(self.superblock, "s_inodes_count")
        for n_inode in range(n_inodes):
            # Obtain inode and calculate offset
            inode = self.volume.get_inode(n_inode)
            offset = inode.offset + reserved_space_offset
            # Obtain data and check if it is all zeros
            data = os.pread(self.fd, len_reserved_space, offset)
            if data != b"\x00\x00":
                count += 1
                self.handle_found_data(n_inode, data, "Reserved space is not empty.", "reserved_space_inode")

        return count

    def check_inode_bitmap_slack_space(self):
        """
        Checks the slack space in the inode bitmap. E2FSCK also checks this.
        Returns:
            1 if the slack space is not empty, 0 otherwise
        """
        inodes_per_group = getattr(self.superblock, "s_inodes_per_group")
        # Calculate number of bytes to skip
        skip_bytes = int(inodes_per_group / 8)
        count = 0
        for gd in self.group_descriptors:
            # Obtain block of inode bitmap
            bitmap = getattr(gd, "bg_inode_bitmap")
            offset = (bitmap * self.block_size) + skip_bytes
            size_slack_space = int(self.block_size - skip_bytes)
            data = os.pread(self.fd, size_slack_space, offset)
            # Can be 0's if INODE_UNINIT is enabled
            if data != b"\xff" * size_slack_space and data != b"\x00" * size_slack_space:
                self.handle_found_data(-1, data, "Slack space in the inode bitmap is not empty.", "inode_bitmap")
                count += 1
        return count

    def check_block_bitmap_slack_space(self):
        blocks_per_group = getattr(self.superblock, "s_blocks_per_group")
        # There is no padding left if this is true.
        if blocks_per_group == (self.block_size * 8):
            return 0

        skip_bytes = int(blocks_per_group / 8)
        count = 0
        size_slack_space = int(self.block_size - skip_bytes)
        for gd in self.group_descriptors:
            # Obtain block of block bitmap
            bitmap = getattr(gd, "bg_block_bitmap")
            offset = (bitmap * self.block_size) + skip_bytes
            data = os.pread(self.fd, size_slack_space, offset)
            # Can be 0's if BLOCK_UNINIT is enabled
            if data != b"\xff" * size_slack_space and data != b"\x00" * size_slack_space:
                self.handle_found_data(-1, data, "Slack space in the block bitmap is not empty.", "block_bitmap")
                count += 1

        return count

    def check_reserved_inodes(self):
        """
        Checks the reserved inodes (9 and 10). These are usually not used.
        Data in these inodes do not necessary mean that there is hidden data, but it is suspicious.
        Returns:
            Number of inodes which are not empty (so at max, 2).
        """
        # At 124: checksum of inode is stored. Skip these, test the rest.
        count = 0
        first_gdt = self.group_descriptors[0]
        start_table = getattr(first_gdt, "bg_inode_table")
        start_checksum: Final = 0x7C
        end_checksum: Final = 0x7E
        inode_size = getattr(self.superblock, "s_inode_size")

        for i in range(9, 11):
            inode = self.volume.get_inode(i)
            offset_inode = inode.offset
            # Calculate offset of the second half, without the checksum
            o_second_half = offset_inode + 126
            # Obtain first and csecond half
            first_half = os.pread(self.fd, start_checksum, offset_inode)
            second_half = os.pread(self.fd, (inode_size - end_checksum), o_second_half)
            if first_half != (b"\x00" * start_checksum) or second_half != (b"\x00" * (inode_size - end_checksum)):
                self.handle_found_multiple_data(i, first_half, second_half, "Reserved inode is not empty; check flags.", "reserved_inode")
                count += 1

        return count

    def check_extended_attributes(self):
        """
        Check if there is data after the size of the extended attributes.
        Returns:
            Number of times there was more data in the extended attributes
        """
        count = 0
        inode_size = getattr(self.superblock, "s_inode_size")
        n_inodes = getattr(self.superblock, "s_inodes_count")
        offset_isize_size: Final = 0x80
        length_standard_inode: Final = 0x80
        for n_inode in range(n_inodes):
            # Obtain inode
            inode = self.volume.get_inode(n_inode)
            # Calculate offset
            offset = inode.offset + offset_isize_size
            # Obtain length of extra isize
            extra_isize = int.from_bytes(os.pread(self.fd, 2, offset), "little")
            # Obtain isize offset
            i_offset = length_standard_inode + extra_isize
            length = inode_size - i_offset
            start_read = inode.offset + i_offset
            data = os.pread(self.fd, length, start_read)
            if data != (b"\x00" * length):
                self.handle_found_data(n_inode, data, "There is more data in the extended attributes than the size"
                                                      "specified in extra_isize.", "extended_attributes")
                count += 1
        return count

    def check_superblock_slack(self):
        """
        Checks the slack of the superblock, if there is any. Also checks all the
        superblock copies.
        Returns:
            Number o
        """
        count = 0
        length_backup_copy: Final = 1024
        minimum_block_size: Final = 2048
        # Impossible if block size <= 1024
        if self.block_size <= length_backup_copy:
            return count

        group_descriptors = self.volume.group_descriptors
        standard_length = self.block_size - length_backup_copy
        for gd in range(len(group_descriptors)):
            if not check_powers(gd):
                continue
            # First SB is a 'special case' - first 1024 are padded for the PBS
            if gd == 0:
                length = self.block_size - minimum_block_size
                if length > 0:
                    data = os.pread(self.fd, length, minimum_block_size)
                    if data != (b"\x00" * length):
                        self.handle_found_data(-1, data, "There is data in the slack of superblock 0", "superblock_slack")
                        count += 1
                continue

            location = ((gd * self.blocks_per_group) * self.block_size) + length_backup_copy
            data = os.pread(self.fd, standard_length, location)
            if data != (b"\x00" * standard_length):
                self.handle_found_data(-1, data, "There is data in the slack of superblock " + str(gd), "superblock_slack")
                count += 1
        return count

    def check_group_descriptor_reserved(self):
        # Calculate right offset based at the block size
        offset = 1
        if self.block_size == 1024:
            offset = 2
        count = 0
        size: Final = 4
        blocks_per_group: Final = getattr(self.superblock, "s_blocks_per_group")
        # Check every GD (backup)
        for gdt in range(len(self.group_descriptors)):
            if not check_powers(gdt):
                continue
            base_location = (gdt * blocks_per_group + offset) * self.block_size
            # Loop through all the GDTs and check if the reserved space is empty.
            for igdt in range(len(self.group_descriptors)):
                location = base_location + 0x3C
                data = os.pread(self.fd, size, location)
                if data != (size * b"\x00"):
                    self.handle_found_data(-1, data, "Reserved data in group descriptor " + str(gdt) + " is not empty.", "gd_reserved")
                    count += 1
                base_location += 64
        return count

    def check_gdt_growth_blocks(self):
        """
        Checks the GDT growth blocks.
        Returns:
            Number of growth blocks where data is hidden
        """
        skip_start = 1
        if self.block_size == 1024:
            skip_start = 2
        # Calculate the number of blocks to skip. +1 to round to 'above'.
        skip_blocks = int((len(self.volume.group_descriptors) * 64) / self.block_size) + 1
        count = 0
        reserved_gdt_blocks = getattr(self.superblock, "s_reserved_gdt_blocks")
        one_too_many = False
        start_bitmap = getattr(self.group_descriptors[0], "bg_block_bitmap") + 1

        # First number is the number of the growth block. Skip these.
        offset_gdt_number: Final = int((reserved_gdt_blocks / 8))

        # Loop through all GDT (backups)
        for group in range(len(self.volume.group_descriptors)):
            if not check_powers(group):
                continue
            start = skip_start + skip_blocks + (group * self.blocks_per_group)
            end = start + reserved_gdt_blocks
            if end == start_bitmap or one_too_many:
                end -= 1
                one_too_many = True

            for i in range(start, end):
                size = self.block_size
                location = (i * size) + offset_gdt_number

                data = os.pread(self.fd, size - offset_gdt_number, location)
                if data != (b"\x00" * (size - offset_gdt_number)):
                    self.handle_found_data(-1, data, "Growth blocks in location " + str(location) + " are not empty.", "growth_blocks")
                    count += 1

        return count

    def check_all(self):
        self.check_reserved_inodes()
        self.check_extended_attributes()
        self.check_superblock_slack()
        self.check_superblock_backup()
        self.check_reserved_space_inodes()
        self.check_partition_boot_sector()
        self.check_inode_bitmap_slack_space()
        self.check_block_bitmap_slack_space()
        self.check_osd2()
        self.check_group_descriptor_reserved()
        self.check_gdt_growth_blocks()
        self.check_file_slack()

        return self.techniques


def init_argparser() -> argparse.ArgumentParser:
    desc = '''\
            A tool to detect hidden data in an EXT4 filesystem image.
            Created by Rajeck Massa.'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=desc)
    parser.add_argument("-f", "--filename", help="The name of the EXT4 image.", required=True)
    parser.add_argument("--log", help="Enable or disable logging", action=argparse.BooleanOptionalAction, required=True)
    parser.add_argument("-s", "--string", help="Specify a string to search for.", nargs="?", const=None)
    return parser


if __name__ == "__main__":
    parser = init_argparser()
    args = parser.parse_args()
    detect = Detect(args.filename, args.string, args.log)
    detect.check_all()
