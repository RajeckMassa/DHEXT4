"""
We willen bijhouden:
- Hoeveel er volledig slagen
- Hoeveel er partieel slagen, en welke dan missen
- Hoeveel er volledig missen
Dus:
if set(x) == set(y): Volledig slagen ++
if set(x) != set(y): Check welke missen, houd die bij

"""
import os

from Catalog import parser
import xml.etree.ElementTree as ET
from Detect import Detect
import argparse

def init_dicts():
    hiding_method_missed = {}

    hiding_method_wrong_positive = {}

    hiding_method_parameters_missed = {}

    hiding_method_parameters_wrong_positive = {}

    total = {}

    success = {}

    return hiding_method_missed, hiding_method_wrong_positive, \
        hiding_method_parameters_missed, hiding_method_parameters_wrong_positive, total, success


def add_to_dict(dict, method):
    if method in dict:
        dict[method] += 1
        return
    dict[method] = 1

def print_info(percentage, h_m_w_p, h_m_m, h_m_p_w_p, h_m_p_m, total, success, correct_found, runs, total_runs):
    print("Status: ", percentage, "%")
    print("Methods with wrong positives: ")
    print(h_m_w_p)
    print("Methods who are missed by the detection tool:")
    print(h_m_m)

    print("-----")
    print("Methods with wrong positives, with parameters: ")
    print(h_m_p_w_p)
    print("Methods who are missed by the detection tool, with parameters: ")
    print(h_m_p_m)
    print("Total runs: ")
    print(total)
    print("Success: ")
    print(success)
    print("Correct till now: ")
    print(correct_found)
    print("runs till now: ")
    print(runs)
    print("Correct: ", correct_found, " total: ", runs, " percentage correct: ",
          (correct_found / runs) * 100, " total 2.0: ", total_runs)


def benchmark(search_string: bool, TechniqueTreePath, ImageTreePath):
    print("Benchmark started, see you in ~ 6 hours...")
    runs = 0
    count = 0
    old_percentage = 0
    total_runs = 4096 * 18
    hiding_method_missed, hiding_method_wrong_positive, \
        hiding_method_parameters_missed, hiding_method_parameters_wrong_positive, total, success = init_dicts()
    # 4095 hiding techniques, 10 for testing
    correct_found = 0
    TechniqueTree = ET.parse(TechniqueTreePath)
    ImageTree = ET.parse(ImageTreePath)
    # Loop through all techniques
    for i in range(0, 4095):
        # Loop through all images
        for j in range(0, 18):
            count += 1
            # Status updates
            percentage_done = int((count / total_runs) * 100)
            if percentage_done % 5 == 0 and old_percentage != percentage_done:
                old_percentage = percentage_done
                print_info(percentage_done, hiding_method_wrong_positive, hiding_method_missed,
                           hiding_method_parameters_wrong_positive, hiding_method_parameters_missed,
                           total, success, correct_found, runs, total_runs)
            # Obtain image
            block_size, inode_size, size = parser.create_image(j, ImageTree)
            # Perform hiding techniques
            success_technique, data_list = parser.get_technique_image(i, "output.dd", TechniqueTree)
            if not success_technique:
                os.remove("output.dd")
                continue
            runs += 1
            # Check if we need to search for specific strings or not
            if search_string:
                detect_obj = Detect.Detect(file_name="output.dd", log=False, string=data_list)
            else:
                detect_obj = Detect.Detect(file_name="output.dd", log=False, string=None)
            # Find all data hiding techniques
            techniques_found = detect_obj.check_all()
            # Obtain the name of the hiding techniques performed
            correct_hided_names = parser.get_technique_list(TechniqueTree.getroot(), i)
            # Add them to the 'performed'-dict
            for method in correct_hided_names:
                add_to_dict(total, method)
            # Check if the sets are 100% the same
            if set(techniques_found) == set(correct_hided_names):
                correct_found += 1
                for method in techniques_found:
                    add_to_dict(success, method)
                continue

            # If not, calculate the false positives and the missed
            false_positives = list(set(techniques_found) - set(correct_hided_names))
            missed = list(set(correct_hided_names) - set(techniques_found))
            # Save the image parameters for both of them, so we can report them
            for method in false_positives:
                combined = (method, block_size, inode_size, size)
                add_to_dict(hiding_method_wrong_positive, method)
                add_to_dict(hiding_method_parameters_wrong_positive, combined)

            for method in missed:
                combined = (method, block_size, inode_size, size)
                add_to_dict(hiding_method_missed, method)
                add_to_dict(hiding_method_parameters_missed, combined)

            os.remove("output.dd")

    print_info(100, hiding_method_wrong_positive, hiding_method_missed,
               hiding_method_parameters_wrong_positive, hiding_method_parameters_missed,
               total, success, correct_found, runs, total_runs)


def init_argparser() -> argparse.ArgumentParser:
    desc = '''\
            Benchmark tool to test the hide/detection tool..
            Created by Rajeck Massa.'''
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=desc)
    argparser.add_argument("--search", help="Search for the string", action=argparse.BooleanOptionalAction, required=True)
    argparser.add_argument("-i", "--imagepath", help="Path to the image catalog.", required=True)
    argparser.add_argument("-t", "--techniquepath", help="Path to the technique catalog.", required=True)

    return argparser


if __name__ == "__main__":
    argparser = init_argparser()
    args = argparser.parse_args()
    image_path = args.imagepath
    technique_path = args.techniquepath
    if args.search:
        benchmark(True, technique_path, image_path)
        exit(0)
    benchmark(False, technique_path, image_path)
