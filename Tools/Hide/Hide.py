import os
import random
import ext4
from typing import Final
import argparse


class Hide:
    def __init__(self, file_name=None, type=None, data=None, inode=None, group=None, log=False):
        if file_name is None or type is None or data is None:
            raise MissingData

        self.file_name = file_name
        self.type = type
        self.data = data
        self.log = log

        self.file = open(self.file_name, "rb")
        self.fd = os.open(self.file_name, os.O_RDWR)
        self.volume = ext4.Volume(self.file, offset=0)
        self.superblock = self.volume.superblock
        self.blocks_per_group = getattr(self.superblock, "s_blocks_per_group")
        self.inode = inode
        self.group = group

        if inode is None:
            self.inode = self.get_random_inode()
        if group is None:
            self.group = 3

    def get_random_inode(self):
        """
        Obtains a random inode from all the possible inodes
        Returns:
            A random inode number
        """
        n_inodes = getattr(self.superblock, "s_inodes_count")
        inode = random.randint(1, n_inodes)
        return inode

    def __del__(self):
        if hasattr(self, "file"):
            self.file.close()
            os.close(self.fd)

    def check_all(self, size: int, data: str):
        """
        Checks if the length of the data which will be hidden is not too large
        for the data hiding technique.
        Returns:
            Size of the data
            Data encoded in bytes
        Excepts:
            If the data is too big
        """
        n_size: Final = size
        n_data = bytes(data, 'utf-8')
        if len(n_data) > size:
            raise SizeException(f"String {data} is {len(n_data)} in size, when the max is {size}")
        return n_size, n_data

    def write_inodes(self, inode: int, offset: int, data: bytes):
        """
        Writes to the specified inode.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        inode_location = self.volume.get_inode(inode)
        location = inode_location.offset + offset
        written = os.pwrite(self.fd, data, location)
        return written, location

    def superblock_slack(self, data: str):
        """
        Responsible for hiding data in the superblock slack space.
        Returns:
            Number of bytes written
            Location where the data is written to
        """

        # Volume size must be larger than 1024 bytes
        if self.volume.block_size <= 1024:
            raise BlockSizeTooSmall

        blocks_per_group = getattr(self.superblock, "s_blocks_per_group")
        # Superblock is always 1024 bytes long
        length_backup_copy: Final = 1024
        location = (self.group * blocks_per_group) * self.volume.block_size + length_backup_copy
        size, data_bytes = self.check_all(self.volume.block_size - length_backup_copy, data)
        written = os.pwrite(self.fd, data_bytes, location)
        return written, location

    def file_slack(self, data: str):
        """
        Responsible for hiding data in the file slack.
        Returns:
            Number of bytes written
            Location where the data is written to
        """

        # Obtain inode
        inode = self.volume.get_inode(self.inode)
        size = inode.__len__()
        try:
            # Get block index of the startblock
            start_block = inode.open_read().block_map[0].disk_block_idx
            # Obtain number of blocks used by the file
            n_blocks = inode.open_read().block_map[0].block_count
            # Calculate end block and how much of the end block is used
            end_block = (start_block + n_blocks - 1) * self.volume.block_size
            block_used = size % self.volume.block_size
            location = end_block + block_used
            # Calculate the size of slack space
            size_to_write = self.volume.block_size - block_used
            size, data_bytes = self.check_all(size_to_write, data)
            written = os.pwrite(self.fd, data_bytes, location)
            return written, location
        except:
            return 0, 0

    def inode_bitmap(self, data: str):
        """
        Responsible for hiding data in the inode bitmaps.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        block_size = self.volume.block_size
        # Obtain the group descriptor table entry
        gdt = self.volume.group_descriptors[0]
        bitmap = getattr(gdt, "bg_inode_bitmap")
        inodes_per_group = getattr(self.superblock, "s_inodes_per_group")
        # Calculate the beginning of the slack space of the inode bitmap
        offset = int((bitmap * block_size) + (inodes_per_group / 8))
        size_slack_space = int(self.volume.block_size - (inodes_per_group / 8))
        size, data_bytes = self.check_all(size_slack_space, data)
        written = os.pwrite(self.fd, data_bytes, offset)
        return written, offset

    def block_bitmap(self, data: str):
        """
        Responsible for hiding data in the block bitmap.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        block_size = self.volume.block_size
        blocks_per_group = getattr(self.superblock, "s_blocks_per_group")
        # Check if there is a slack space
        if blocks_per_group == (block_size * 8):
            return 0, 0
        offset = (blocks_per_group / 8)
        size = blocks_per_group - offset
        size, data_bytes = self.check_all(size, data)
        gd = self.volume.group_descriptors
        bitmap = getattr(gd[0], "bg_block_bitmap")
        location = int((bitmap * block_size) + offset)
        written = os.pwrite(self.fd, data_bytes, location)
        return written, location

    def gd_reserved(self, data: str):
        """
        Responsible for hiding data in the reserved area for group descriptors.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        # Add the padding if the block size is 1024
        offset = 1
        if self.volume.block_size == 1024:
            offset = 2
        reserved_offset: Final = 0x3C
        size, data_bytes = self.check_all(2, data)
        group: Final = self.group
        size = self.volume.block_size
        sb = self.volume.superblock
        blocks_per_group = getattr(sb, "s_blocks_per_group")
        location = (((group * blocks_per_group) + offset) * size) + reserved_offset
        written = os.pwrite(self.fd, data_bytes, location)
        return written, location

    def reserved_space_inode(self, data: str):
        """
        Responsible for hiding data in the reserved space in inodes.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        offset: Final = 0x7A
        size, data_bytes = self.check_all(2, data)
        return self.write_inodes(self.inode, offset, data_bytes)

    def reserved_inodes(self, data: str):
        """
        Responsible for hiding data in reserved inodes.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        offset: Final = 4
        size, data_bytes = self.check_all(4, data)
        return self.write_inodes(self.inode, offset, data_bytes)

    def osd2(self, data: str):
        """
        Responsible for hiding data in the OSD2 field.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        offset: Final = 0x7E
        size, data_bytes = self.check_all(2, data)
        return self.write_inodes(self.inode, offset, data_bytes)

    def partition_boot_sector(self, data: str):
        """
        Responsible for hiding data in the partition boot sector.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        offset: Final = 0
        size, data_bytes = self.check_all(1024, data)
        written = os.pwrite(self.fd, data_bytes, offset)
        return written, offset

    def backup_superblock(self, data: str):
        """
        Responsible for hiding data in the superblock backup.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        # Padding if the block size is 1024
        offset = 0
        if self.volume.block_size == 1024:
            offset = 1
        sb = self.volume.superblock
        block_size = self.volume.block_size
        blocks_per_group = getattr(sb, "s_blocks_per_group")
        gd = self.volume.group_descriptors
        # Check if there are minimal 2 group descriptors
        if len(gd) < 3:
            raise TooFewBlockGroups

        size, data_bytes = self.check_all(1024, data)
        location = ((blocks_per_group * self.group) + offset) * block_size
        written = os.pwrite(self.fd, data_bytes, location)
        return written, location

    def extended_attributes(self, data: str):
        """
        Responsible for hiding data in the extended attributes of inodes.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        # First 3 bytes (156-159) are (often) not empty, so don't overwrite that
        # to not raise suspicion. So, offset starts at 0x9F
        offset: Final = 0x9F
        size, data_bytes = self.check_all(100, data)
        return self.write_inodes(self.inode, offset, data_bytes)

    def growth_blocks(self, data: str):
        """
        Responsible for hiding data in growth blocks.
        Returns:
            Number of bytes written
            Location where the data is written to
        """
        # Calculate number of blocks occupied by the group descriptor table entries
        skip_blocks = int((len(self.volume.group_descriptors) * 64) / self.volume.block_size) + 1
        reserved_gdt_blocks = getattr(self.superblock, "s_reserved_gdt_blocks")
        # Padding if the block size is 1024
        skip_start = 1
        if self.volume.block_size == 1024:
            skip_start = 2
        start = skip_start + skip_blocks + (self.group * self.blocks_per_group)
        size = int(reserved_gdt_blocks * self.volume.block_size - (reserved_gdt_blocks / 8))
        size, data_bytes = self.check_all(size, data)
        location = start * self.volume.block_size + int(reserved_gdt_blocks / 8)
        written = os.pwrite(self.fd, data_bytes, location)
        return written, location

    def check_if_possible(self):
        """
        Checks if a hiding method is possible on the image.
        Returns:
            True if possible, False otherwise
        """
        match self.type:
            case "block_bitmap":
                if self.blocks_per_group == (self.volume.block_size * 8):
                    return False
                return True
            case "backup_superblock":
                if len(self.volume.group_descriptors) < 3:
                    return False
                return True
            case "superblock_slack":
                if self.volume.block_size <= 1024:
                    return False
                return True
            case "file_slack":
                inode = self.volume.get_inode(self.inode)
                if not inode.is_file:
                    return False
                try:
                    inode.open_read().block_map[0].disk_block_idx
                except:
                    return False
                return True
            case _:
                return True

    def get_hiding_technique(self):
        """
        Calls the right method based on the specified hiding technique.
        """
        match self.type:
            case "inode_bitmap":
                return self.inode_bitmap(self.data)
            case "block_bitmap":
                return self.block_bitmap(self.data)
            case "gd_reserved":
                return self.gd_reserved(self.data)
            case "reserved_space_inode":
                return self.reserved_space_inode(self.data)
            case "reserved_inode":
                return self.reserved_inodes(self.data)
            case "partition_boot_sector":
                return self.partition_boot_sector(self.data)
            case "backup_superblock":
                return self.backup_superblock(self.data)
            case "extended_attributes":
                return self.extended_attributes(self.data)
            case "growth_blocks":
                return self.growth_blocks(self.data)
            case "osd2":
                return self.osd2(self.data)
            case "file_slack":
                return self.file_slack(self.data)
            case "superblock_slack":
                return self.superblock_slack(self.data)
            case _:
                raise UnknownHidingMethod("Hiding technique " + self.type + " isn't implemented!")

    def logger(self, written_bytes: int, location: int):
        print(f"[LOG] Written {written_bytes} bytes to {location}")


def init_argparser() -> argparse.ArgumentParser:
    desc = '''\
            A tool to hide data in an EXT4 filesystem image.
            Created by Rajeck Massa.'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=desc)
    parser.add_argument("-f", "--filename", help="The name of the EXT4 image.", required=True)
    parser.add_argument("-d", "--data", help="The data which needs to be hidden.", required=True)
    parser.add_argument("-t", "--technique", help="The hiding technique which needs to be used.", required=True)
    parser.add_argument("--log", help="Enable or disable logging", action=argparse.BooleanOptionalAction, required=True)
    parser.add_argument("-i", "--inode", help="Specify a inode to hide the data.", nargs="?", const=None)
    parser.add_argument("-g", "--group", help="Specify a group to hide the data.", nargs="?", const=None)
    return parser


if __name__ == "__main__":
    parser = init_argparser()
    args = parser.parse_args()
    HideInstance = Hide(args.filename, args.technique, args.data, args.inode, args.group)
    bytes, location_hidden = HideInstance.get_hiding_technique()
    if args.log:
        HideInstance.logger(written_bytes=bytes, location=location_hidden)


# Custom exceptions used in the hiding tool
class SizeException(Exception):
    """
    Thrown when the size of the data is too big for the hiding spot
    """


class UnknownHidingMethod(Exception):
    """
    Thrown when the hiding method isn't known
    """


class FileNotFound(Exception):
    """
    Thrown when the file isn't found
    """


class TooFewBlockGroups(Exception):
    """
    Thrown when there are too few block groups
    """


class BlockSizeTooSmall(Exception):
    """
    Thrown when the block size is too small
    """


class MissingData(Exception):
    """
    Thrown when there is data missing.
    """
