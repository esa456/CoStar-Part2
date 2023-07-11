# CoStar-Part2
CoStar project part 2

The purpose of this project is to scrape the data specified in 'https://bradvisors.com/listing'

# Assumptions
For the purpose of this task an assumption was made that for sale/under contract properties were available immediately.

For rent properties overall availability could not be inferred as some had multiple floors and so the sale_stage of these properties would be set to 'N/A', however, more details on that would be found in spaces, if applicable.

# Installation and run
To deploy and install the dependencies to this project run _pip install -r requirements.txt_

To run it (please ensure you are in the directory of this project) _python task2.py_

# Please Note
A second file is available in this repository that includes functionality to allow for the scraping of demographical data, unfortunately I was not able to run integration tests on this piece of code and so was not able to include it in my final solution. If you are interested you can use the following command to run it below. (As an integration test was not completed, it may run with errors).

To run it (please ensure you are in the directory of this project) _python task2-withdem.py_
