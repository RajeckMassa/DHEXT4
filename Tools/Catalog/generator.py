import itertools
import xml.etree.ElementTree as ET
from itertools import combinations, product
from xml.etree.ElementTree import Element

def add_technique(name: str, data: str, inode: str, group: str, techniques: ET.Element):
    # Adds an technique to an entry
    technique = ET.SubElement(techniques, "technique")
    ET.SubElement(technique, "name").text = name
    ET.SubElement(technique, "data").text = data
    ET.SubElement(technique, "inode").text = inode
    ET.SubElement(technique, "group").text = group


def generate_info(block_size: str, inode_size: str,
                   size: str, image: ET.Element):
    # Generates all the information about an image
    info = ET.SubElement(image, "info")
    ET.SubElement(info, "block_size").text = block_size
    ET.SubElement(info, "inode_size").text = inode_size
    ET.SubElement(info, "size").text = size


def create_image(image_id: str, root: ET.Element, block_size: str,
                 inode_size: str, size: str) -> Element:
    # Creates a new image entry in the catalog
    image = ET.SubElement(root, "image", id=image_id)
    generate_info(block_size, inode_size, size, image)
    return image


def create_technique_image(image_id: str, root: ET.Element) -> tuple[ET.Element, ET.Element]:
    # Creates a new technique entry in the catalog
    image = ET.SubElement(root, "image", id=image_id)
    techniques = ET.SubElement(image, "techniques")
    return image, techniques


def generate_image_catalog():
    check = 0
    root = ET.Element("root")
    # -b
    block_sizes = [1024, 2048, 4096]
    # -I
    inode_sizes = [256, 512]
    # Size of the images.
    sizes = [1024, 2048, 2560]
    # Obtain all the possible combinations and add them to the catalog
    all_combinations = list(product(block_sizes, inode_sizes, sizes))
    for block_size, inode_size, size in all_combinations:
        create_image(str(check), root, str(block_size), str(inode_size),
                     str(size))
        check += 1

    tree = ET.ElementTree(root)
    tree.write("ImageCatalog.xml")


def generate_techniques_catalog():
    # All the possible techniques
    techniques_and_data = [("inode_bitmap", "inodeBM", "-1", "-1"), ("block_bitmap", "blockBM", "-1", "-1"),
                           ("gd_reserved", "gd", "-1", "3"), ("reserved_space_inode", "rs", "22", "-1"),
                           ("reserved_inode", "resI", "9", "-1"), ("partition_boot_sector", "PartitionBootSector", "-1", "-1"),
                           ("backup_superblock", "backup_superblock", "-1", "3"),
                           ("extended_attributes", "extendAttri", "23", "-1"), ('file_slack', 'fileslack', "13", "-1"),
                           ("growth_blocks", "growthBlock", "-1", "3"), ("osd2", "os", "22", "-1"), ("superblock_slack", "s_slack", "-1", "3")]
    root = ET.Element("root")
    check = 0
    # Obtain all possible combinations of the hiding techniques and add them to the catalog
    for n in range(len(techniques_and_data) + 1):
        for subset in itertools.combinations(techniques_and_data, n):
            if len(subset) == 0:
                continue
            image, techniques = create_technique_image(str(check), root)
            for name, data, inode, group in subset:
                add_technique(name, data, inode, group, techniques)
            check += 1

    tree = ET.ElementTree(root)
    tree.write("Catalog.xml")


generate_techniques_catalog()
generate_image_catalog()
