from Catalog import parser
import argparse
import xml.etree.ElementTree as ET
argparser = argparse.ArgumentParser()
argparser.add_argument("-i", "--id", type=int, required=True)
argparser.add_argument("-n", "--name", type=str, required=True)
args = argparser.parse_args()

technique_id = args.id
image_name = args.name
TechniqueTree = ET.parse('Catalog/Catalog.xml')
parser.get_technique_image(technique_id, image_name, TechniqueTree)