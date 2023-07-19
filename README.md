# Automatic Data Hiding detection in EXT4
This project is created for my bachelor thesis "Creating a Detection Tool for Data Hiding Techniques
in EXT4" at University Leiden, Netherlands. The bachelor thesis was supervised by dr. K. F. D. Rietveld.  
This project contains a detection, hide and benchmark tool, all written in Python. All the tools require Python 3.10. All the tools are CLI programs,
which means they can be used from the command line.

# Hide tool
To hide data, the following command can be used:  
`python3 Hide.py -f path/to/image.dd -d dataToHide -t techniqueNrToUse --log/--no-log`  
All the techniques used to hide data are listed in the thesis, which can be found ... .

# Detection tool
To detect any hidden data, the following command can be used:  
`python3 Detect.py -f path/to/image.dd (-s string) --log/-no-log`
With the -s command, one can explicity search for a string, and the program will only report data found which
has the requested string in it.

# Benchmark
To run the benchmark, the following command can be used:  
`python3 BenchmarkDHEXT4.py -i path/to/imagecatalog.xml -t path/to/techniquecatalog.xml --search/--no-search`
The image and technique catalog can be generated using the generator program found in the Catalog map. With --search/--no-search, 
one can run the benchmark while the detection tool searches for a string, or the detection tool searches for the 'unknown'.

It is possible to create your own Hide and Detection class to work with the benchmark. These classes have a few required methods and initializers to work with the benchmark tool:

### Detection Class
The detection class requires the following initalizor: `Detect(file_name, log, string)`. Hereby is `file_name` a String which obtains the file name of the image, `log` is a Boolean which controls the logging output and `string` is a list of Strings, which contains words to search for. If `string` is None, the program searches for the 'unknown'

Furthermore, a method called `check_all()` is required, which calls all the detection methods implemented in the class. This method returns a list of Strings, with the names of all found data hiding techniques.

### Hiding class
The hiding class requires the following initalizor: `Hide.Hide(file_name, type, data, inode, group)`.  Hereby is `file_name` a String which obtains the file name of the image, `type` the hiding technique, `data` the data which needs to be hidden, `inode` the inode number of where the data must be hidden and `group` the group number of where the data must be hidden. 

Furthermore, a method called `check_if_possible()` is required, which checks if it is possible to perform the given data hiding technique on the image (f.e., check if block size is > 1024 for Superblock Slack).

At last, a method called `get_hiding_technique()` is required. This method calls the right hiding method based on the 'Type' input, and performs the hiding technique on the image.

By changing the Detect import in BenchmarkDHEXT4.py and the Hide import in Catalog/parser.py, one can now use it's own implementation of a Detection and Hide class for the benchmark
