"""This file focuses on part2 of the CoStar coding challenge and highlights the functions used
to ascertain the output provided in github
"""
############################################################################################
import re
import json
from time import sleep
from datetime import date
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from webdriver_manager.chrome import ChromeDriverManager

############################################################################################
def emulate_browser():
    """This function instantiates the browser"""

    options = Options()
    options.add_argument("--headless")
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    return browser


############################################################################################
def listings_results(link):
    """This function ultimately scrapes all the results returned by the link provided"""
    # Instantiate browser
    browser = emulate_browser()

    # Create list for results
    results = []

    # Navigate to page
    browser.get(link)
    sleep(1)

    # All content is hosted within an iframe so find this
    iframe = browser.find_element(By.XPATH, '//*[@id="buildout"]/iframe')

    # and switch to it
    browser.switch_to.frame(iframe)

    # find the pagination bar
    nav_bar = browser.find_element(
        By.XPATH, "/html/body/div[3]/form/div/div/div[2]/div[3]/div[3]/div"
    ).text
    # split the result by \n to find the max num of pages
    nav_split = nav_bar.split("\n")

    # Loop through page elements
    for i in range(1, int(nav_split[-1]) + 1):
        page_results = browser.find_elements(
            By.CSS_SELECTOR, 'div[class="card-body p-0"]'
        )

        # Scrape the current page results
        scraped_results = scrape_results(page_results)

        # Append the scraped data to the results list
        results.extend(scraped_results)

        # Click through the pages using the num of pages (nav_split)
        try:
            sleep(1)
            browser.find_element(By.CSS_SELECTOR, f'div[data-page="{i}"]').click()
            sleep(2)
        # Do this until there are no more
        except NoSuchElementException:
            print("End of pages")

    # Terminate instance
    browser.close()

    return results


############################################################################################
def scrape_results(results):
    """This function retrieves the 'scraped_at', 'url', 'building_name',
    'address', 'transaction_type' and 'sale_or_rent' of each result"""
    scraped_results = []

    # Loop through results
    for result in results:

        # Return the text of web element
        info = result.text

        # Split by \n
        info_list = info.split("\n")

        # Get the current timestamp
        current_time = date.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

        # Transaction_type is the first element in the list
        transaction_type = info_list[0]

        # If the property is a lease, format sale_or_rent
        if "lease" in transaction_type.lower():
            transaction_type = "for rent"
            sale_or_rent = "Lease Rate " + info_list[4]

        # Otherwise format the same variable differently
        else:
            transaction_type = transaction_type.lower()
            sale_or_rent = "Price " + info_list[3]

        building_name = info_list[1]
        address = info_list[2]

        # Retrieve address
        if "|" in address:
            address_parts = address.split("|")
            formatted_address = building_name + ", " + address_parts[1]
        else:
            formatted_address = building_name + ", " + address

        # Retrieve url
        page_link = re.findall(r'href="(.*?)"', result.get_attribute("innerHTML"))

        # Add everything to an initial dictionary
        intial_dict = {
            "scraped_at": current_time,
            "url": page_link[0],
            "building_name": building_name,
            "address": formatted_address,
            "transaction_type": transaction_type,
            "sale_or_rent": sale_or_rent,
        }

        # Append the current sub-dictionary to the scraped_results list
        scraped_results.append(intial_dict)

    return scraped_results


############################################################################################
def individual_page(results):
    """This function pools the rest of the data from each webpage into a dictionary"""

    # Instantiate browser
    browser = emulate_browser()

    #counter = 0
    # Loop through results
    for result in results:

        # Retrieve the 'url' and 'transaction' for each result
        link = result["url"]
        transaction_type = result["transaction_type"]

        # Set the page load time to 10 seconds
        # If it doesn't load within 10 seconds an error will be thrown
        browser.set_page_load_timeout(10)

        try:
            # Retrieve result page
            browser.get(link)

            # before switching to iframe gather 'language' and 'country'
            basic_info = browser.find_element(By.XPATH, "/html").get_attribute("lang")
            basic_properties = basic_info.split("-")

            # Switch to element that hosts content
            iframe = browser.find_element(By.XPATH, '//*[@id="buildout"]/iframe')
            browser.switch_to.frame(iframe)

            # Retrieve 'latitude' and 'longitude'
            coordinates_list = coordinates(browser)

            # Retrieve 'description'
            description_content = description(browser)

            # Retrieve the property details which holds 'building_type', 'size'
            # 'building_type' info
            property_content = property_details(browser)

            # Retrieve 'contacts' info
            brokers = contacts_filter(browser)

            # Retrieve 'brochure_link' info
            files = documents(browser)

            # Retrieve 'spaces' info
            spaces_content = spaces(browser)

            # Assume that for sale or under contract properties are available
            if transaction_type == ("for sale", "under contract"):
                sale_stage = "available"

            # 'sale_stage' for lease properties cannot be inferred, please see spaces
            else:
                sale_stage = "N/A"

            building_type = extract_data_from_list(property_content, "Property Type")
            building_size = extract_data_from_list(property_content, "Building Size")

            # Lease and sale properties reference 'size'
            if transaction_type != ("for rent", "for sale"):
                size = extract_data_from_list(property_content, "Size")

            # Under contract properties reference 'total lot size'
            else:
                size = extract_data_from_list(property_content, "Total Lot Size")

            # Retrieve 'demographic' info
            # demographics = dem(browser)

            # Update dictionary with new info
            result.update(
                {
                    "sale_stage": sale_stage,
                    "country": basic_properties[1].lower(),
                    "language": basic_properties[0],
                    "latitude": coordinates_list[0],
                    "longitude": coordinates_list[1],
                    "description": description_content,
                    "building_type": building_type,
                    "building_size": building_size,
                    "size": size,
                    "contacts": brokers,
                    "brochure_link": files,
                    "spaces": spaces_content,
                }
            )

            print(result)

        # Exception thrown if page doesn't load in 10 seconds
        except TimeoutException:

            # Move to next element
            continue

    # Close instance
    browser.close()

    return results


############################################################################################
def coordinates(browser):
    """This function retrieves the latitude and longitude information"""

    coordinates_list = []

    # Look for the map section
    coords = browser.find_element(By.XPATH, '//*[@id="map"]').get_attribute("outerHTML")

    # find coordinate elements
    latitude = re.findall(r'data-latitude="(.*?)"', coords)
    longitude = re.findall(r'data-longitude="(.*?)"', coords)

    # if latitude is not found try another way
    if len(latitude) == 0:
        latitude = re.findall(r'lat="(.*?)"', coords)

    coordinates_list.append(latitude[0])

    # if longitude is not found try another way
    if len(longitude) == 0:
        longitude = re.findall(r'lng="(.*?)"', coords)

    # Add results to a list
    coordinates_list.append(longitude[0])

    return coordinates_list


############################################################################################
def description(browser):
    """This function retrieves the details found in the description section"""

    description_list = []

    # Try to find description element
    try:
        description_data = browser.find_element(
            By.XPATH, '//*[@id="overview"]/div/div[1]/div[3]'
        )

    # If not found, look in another place
    except NoSuchElementException:
        description_data = browser.find_element(
            By.XPATH, '//*[@id="overview"]/div/div[1]/div/section[4]'
        )

    description_elements = description_data.find_elements(By.CSS_SELECTOR, "p")

    # Loop through the retreived data and add text to list
    for j in description_elements:
        description_list.append(j.text)

    return description_list


############################################################################################
def property_details(browser):
    """This function retrieves the info found in property details"""

    prop_list = []

    # Look for property_details element
    prop_details = browser.find_elements(
        By.CSS_SELECTOR, 'div[class="summary-table-split-item pr-sm-3"]'
    )

    # If not found look elsewhere
    if len(prop_details) == 0:
        prop = browser.find_element(
            By.CSS_SELECTOR, 'table[class="table COMPONENT__table"]'
        )
        prop_details = prop.find_elements(By.CSS_SELECTOR, "td")

    # Loop through these elements and add data to list
    for i in prop_details:
        prop_list.append(i.text)

    # Look for the occurrence of a colon
    has_colon = any(":" in element for element in prop_list)

    if has_colon:
        # Join the current elem with the next in a step size of 2
        # (as headers and results were returned in the same list)
        prop_list = [
            prop_list[i] + " " + prop_list[i + 1] for i in range(0, len(prop_list), 2)
        ]

    return prop_list


############################################################################################
def extract_data_from_list(description_list, filter_string):
    """This function extracts descriptive information from a list"""

    # Loop through elemts in list
    for elem in description_list:

        # If the info we want appears in the element
        if filter_string in elem:

            # If it contains a : or \n
            if ":" in elem or "\n" in elem:

                # Split the info by those
                description_split = re.split(r":|\n", elem)
                description_value = description_split[-1].strip()

        # If it doesn't contain the info we want
        else:
            description_value = None

            return description_value

    return None


############################################################################################
def contacts(browser):
    """This function retrieves the broker information"""

    brokers_details = []

    # Look for brokers element
    try:
        brokers = browser.find_element(By.CSS_SELECTOR, 'div[class="col-12 col-md-3"]')
        brokers_element = brokers.find_elements(
            By.CSS_SELECTOR, 'div[class="col-9 pl-3"]'
        )

    # If not found look elsewhere
    except NoSuchElementException:
        brokers_element = browser.find_elements(
            By.CSS_SELECTOR, 'div[class="pdt-broker  py-1 mb-4 d-flex"]'
        )

    # Loop through info and add to list
    for i in brokers_element:
        brokers_details.append(i.text)

    return brokers_details


############################################################################################
def contacts_filter(browser):
    """This function filters and categorises the relevant broker information"""

    # Retrieve broker info
    contacts_list = contacts(browser)

    brokers_list = []

    # Loop through each broker
    for contact_details in contacts_list:

        # Split info by \n
        details = contact_details.split("\n")

        contact_dict = {}
        telephone_list = []

        # Loop through the elements in details
        for deets in details:

            # Look for this pattern
            matches = re.findall(r"\d{3}\.\d{3}\.\d{4}", deets)
            if matches:

                # Extract only the digits from the string
                digits = re.sub(r"\D", "", deets)

                # Format the digits as 'tel:+1(XXX)XXX-XXXX'
                formatted_phone = f"tel:+1({digits[:3]}){digits[3:6]}{digits[6:]}"

                # Add info to a list
                telephone_list.append(formatted_phone)

                # Add list to dictionary
                contact_dict.update({"telephone": telephone_list})

            # If there is an @
            if "@" in deets:

                # Update dictionary with email
                email = deets
                contact_dict.update({"email": email})

        # Update dictionary with name
        contact_dict.update({"name": details[0]})

        brokers_list.append(contact_dict)

    return brokers_list


############################################################################################
def documents(browser):
    """This function retrieves the brochure_links"""

    # Hosted in iframe so prefix is needed
    iframe_link_prefix = "https://buildout.com"
    link_list = []

    # Look for the documents taband elements
    try:
        document = browser.find_element(By.XPATH, '//*[@id="documents"]')
        links = document.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')

        # Loop through resulting links
        for link in links:
            element = link.get_attribute("outerHTML")
            document_link = re.findall(r'href="(.*?)"', element)

            # Add to list
            link_list.append(iframe_link_prefix + document_link[0])

    # If no documents tab
    except NoSuchElementException:
        link_list = None

    return link_list


############################################################################################
def spaces(browser):
    """This function retrieves the infomation found in the spaces section"""

    try:
        # Look for spaces tab
        spaces_content = browser.find_element(By.XPATH, '//*[@id="spaces"]')
        try:
            # Using web page 1s template find element
            table1 = spaces_content.find_elements(
                By.CSS_SELECTOR, 'div[class="section js-lease-space pt-0"]'
            )
            # Check if table1 is empty
            if not table1:
                # Use method to scrape web page 2
                table2 = spaces_content.find_elements(
                    By.CSS_SELECTOR, 'td[class="p-4"]'
                )
                # Retrieve content from table
                spaces_list = table_content(table2, "table", "table")

            # if table1 isn't empty
            else:
                spaces_list = table_content(table1, "div", "row")

        # To cover our selves we try to scrape using web page 1s template again
        except NoSuchElementException:
            table2 = spaces_content.find_elements(By.CSS_SELECTOR, 'td[class="p-4"]')

            # Retrieve content from table
            spaces_list = table_content(table2, "table", "table")

            # Check if both table1 and table2 are empty
        if not table1 and not table2:
            spaces_list = None

    # If can't find any data
    except NoSuchElementException:
        spaces_list = None

    return spaces_list


############################################################################################
def table_content(table, element1, element2):
    """This function retrieves info from the tables"""
    spaces_list = []

    # Loop through tables
    for tab in table:
        spaces_dict = {}

        # Get header
        data = tab.get_attribute("innerHTML")
        match = re.findall(r"<h5>(.*?)</h5>", data)
        spaces_dict.update({"title": match[0]})

        # Retrieve data from table
        content = tab.find_element(
            By.CSS_SELECTOR, f'{element1}[class="{element2}"]'
        ).get_attribute("outerHTML")

        # For web page style 1, look for content like this
        # We retrieve the headers and fields here
        if element2 == "row":
            headers = re.findall(r"<th>(.*?)</th>", content)
            fields = re.findall(r"<td>(.*?)</td>", content)

        # For web page style 2, look for content like this
        # We retreive the headers and fields here plus additional cleaning
        if element2 == "table":
            headers = re.findall(r"<b>(.*?)</b>", content)
            dirty_fields = re.findall(r"<td>(.*?)</td>", content)
            fields = [
                item
                for item in dirty_fields
                if not item.startswith("<b>") and not item.endswith("</b>")
            ]

        # Loop through both lists and match the corresponding headers and fields
        for header, field in zip(headers, fields):

            if header == "Space Type":
                spaces_dict.update({"space type": field})

            if header == "Lease Term":
                spaces_dict.update({"rent time": field})

            if header == ("Space Available", "Space Size"):
                spaces_dict.update({"size": field})

            if header == "Lease Rate":
                spaces_dict.update({"lease rate": field})

            # Also add extra content to dictionary
            else:
                spaces_dict.update({header.lower(): field.lower()})

        spaces_list.append(spaces_dict)

    return spaces_list


############################################################################################
def dem(browser):
    """This function retrieves demographical information"""
    dem_list = []

    # Look for demographics tab and search for data
    try:
        demographic_content = browser.find_element(By.XPATH, '//*[@id="demographics"]')
        dem_element = demographic_content.find_elements(
            By.CSS_SELECTOR, 'div[class="pdt-demographics"]'
        )
        dem_list = dem_content(dem_element)

    # If it doesn't exist
    except NoSuchElementException:
        dem_list = None

    return dem_list


############################################################################################
def dem_content(dem_element):
    """This function both scrapes and formats demographical data"""

    # For each element in the demographic table
    for dem_e in dem_element:

        data = dem_e.get_attribute("innerHTML")

        # titles
        match = re.findall(r'<th scope="col">(.*?)</th>', data)
        distances = [item for item in match if item != ""]

        # Find number of titles
        cols = len(distances)

        content = dem_e.find_element(
            By.CSS_SELECTOR, 'table[class="table"]'
        ).get_attribute("outerHTML")

        # Retrieve categories and data
        headers = re.findall(r"<b>(.*?)</b>", content)
        dirty_fields = re.findall(r"<td>(.*?)</td>", content)
        fields = [
            item
            for item in dirty_fields
            if not item.startswith("<b>") and not item.endswith("</b>")
        ]

        # sort the data
        sublists = [fields[i : i + cols] for i in range(0, len(fields), cols)]
        print("data sorted")

        # Assign the data to it's respective columns
        new_list = []
        for sub in sublists:
            sub_list = []
            for distnce, value in zip(distances, sub):
                sub_dict = {distnce: value}
                sub_list.append(sub_dict)

            new_list.append(sub_list)

        # Assign the data to its respective categories
        final_list = []
        for header, sorted_value in zip(headers, new_list):
            final_dict = {header: sorted_value}
            final_list.append(final_dict)

    return final_list


############################################################################################
def output(link):
    """This function gathers all our data and exports it to a json file"""

    # Retrieve all information in dictionary format
    results = listings_results(link)
    output_dict = individual_page(results)

    # Convert dictionary to JSON formatted string with indentation for readability
    output_json = json.dumps(output_dict, indent=4)

    # Export this data to file
    with open("output.json", "w") as file:
        file.write(output_json)


############################################################################################
def main():
    """This is the main function"""


if __name__ == "__main__":

    LINK = "https://bradvisors.com/listings/"

    output(LINK)
