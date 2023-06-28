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
