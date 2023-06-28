import xml.etree.ElementTree as ET
from typing import Tuple
from itertools import combinations
from xml.etree.ElementTree import Element
import sys
# Ugly fix to import the hide-tool.
sys.path.append('../Hide')
from Hide import Hide
import os

def create_image(id, tree, name="output.dd"):
    """
    Creates an image with the specified ID.
    Returns:
        Block size of the image
        Inode size of the image
        Size of the image
    """
    # Obtain root of element
    root = tree.getroot()
    # Obtain the right entry
    element = root.find('./image[@id="' + str(id) + '"]')
    # Obtain all the info
    infos = element.findall('./info')
    for info in infos:
        # Obtain the right parameters
        block_size = info.find('./block_size').text
        inode_size = info.find('./inode_size').text
        size = info.find('./size').text
        count = int((int(size) * 17000) / int(block_size))
        # Fill the image with 0's
        dd_cmd = "dd status=none if=/dev/zero of=" + name + " bs=" + str(block_size) + " count=" + str(count)
        # Create the image
        mkfs_cmd = "mkfs.ext4 -q -g 1248 -b " + block_size + " -I " + inode_size + " -F " + name
        # Copy a test-file to the image
        mount_cmd = "sudo mount " + name + " Catalog/MountDir/"
        cpy_cmd = "sudo cp Catalog/test.txt Catalog/MountDir/"
        umount_cmd = "sudo umount Catalog/MountDir/"
        # Use the commands
        os.system(dd_cmd)
        os.system(mkfs_cmd)
        os.system(mount_cmd)
        os.system(cpy_cmd)
        os.system(umount_cmd)
        return block_size, inode_size, size


def get_technique_image(id, image_name, tree):
    """
    Performs hiding techniques on an image
    Returns:
        False, data_list if one of the techniques can't be performed
        True, data_list if all the techniques can be performed.
    """
    root = tree.getroot()
    element = root.find('./image[@id="' + str(id) + '"]')
    techniques = element.findall('./techniques/technique')
    # Contains all the techniques with the right parameters
    check_list = []
    # Contains all the data which is hidden
    data_list = []
    for technique in techniques:
        name = technique.find('./name').text
        data = technique.find('./data').text
        inode = int(technique.find('./inode').text)
        group = int(technique.find('./group').text)
        check_list.append((name, data, inode, group))
    # Check if all the hiding techniques are possible
    for name, data, inode, group in check_list:
        hide_data = Hide.Hide(file_name=image_name, type=name, data=data, inode=inode, group=group)
        if not hide_data.check_if_possible():
            return False, data_list
    # Perform all the data hiding techniques
    for name, data, inode, group in check_list:
        hide_data = Hide.Hide(file_name=image_name, type=name, data=data, inode=inode, group=group)
        hide_data.get_hiding_technique()
        data_list.append(data)

    return True, data_list


def get_technique_list(root, id):
    """
    Obtain the names of all the hiding techniques from the specified ID
    Returns:
        List of all the names
    """
    names = []
    element = root.find('./image[@id="' + str(id) + '"]')

    techniques = element.findall('./techniques/technique')
    for technique in techniques:
        name = technique.find('./name').text
        names.append(name)
    return names
