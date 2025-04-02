import re
import json
from pathlib import Path

#Functions to make DACS dates from timestamps and ISO dates
def stamp2DACS(timestamp):
	calendar = {"01": "January", "02": "February", "03": "March", "04": "April", "05": "May", "06": "June", "07": "July", "08": "August", "09": "September", "10": "October", "11": "November", "12": "December"}
	stamp = timestamp[:8]
	year = stamp[:4]
	month = stamp[4:6]
	day = stamp[-2:]
	normal = year + "-" + month + "-" + day
	if day.startswith("0"):
		day = day[-1:]
	dacs = year + " " + calendar[month] + " " + day
	return dacs, normal
	
def iso2DACS(normalDate):
	calendar = {'01': 'January', '02': 'February', '03': 'March', '04': 'April', '05': 'May', '06': 'June', '07': 'July', '08': 'August', '09': 'September', '10': 'October', '11': 'November', '12': 'December'}
	if "-" in normalDate:
		if normalDate.count('-') == 1:
			year = normalDate.split("-")[0]
			month = normalDate.split("-")[1]
			displayDate = year + " " + calendar[month]
		else:
			year = normalDate.split("-")[0]
			month = normalDate.split("-")[1]
			day = normalDate.split("-")[2]
			if day.startswith("0"):
				displayDay = day[1:]
			else:
				displayDay = day
			displayDate = year + " " + calendar[month] + " " + displayDay
	else:
		displayDate = normalDate
	return displayDate


def extract_years(date_string):
    # Initialize an empty set to store unique years
    years = set()

    # Regular expression to match year ranges, e.g., "1988-2001"
    range_pattern = r'(\d{4})-(\d{4})'
    # Regular expression to match individual years in text (e.g., "1988 July 29")
    individual_year_pattern = r'(\d{4})'

    # Find all year ranges and individual years in the date string
    ranges = re.findall(range_pattern, date_string)
    individual_years = re.findall(individual_year_pattern, date_string)

    # Add years from the ranges to the set (inclusive)
    for start, end in ranges:
        years.update(range(int(start), int(end) + 1))  # `range` is inclusive of start but exclusive of end

    # Add individual years directly to the set
    years.update(int(year) for year in individual_years)

    # Return the sorted list of unique years
    return sorted(years)

def write2disk(object, collection_id):
	# takes a jsonmodel object and writes it to disk for testing

	test_path = Path.home() / "description_harvester"
	test_path.mkdir(parents=True, exist_ok=True)
	out_path = test_path / f"{collection_id}.json"

	with open(out_path, "w") as file:
		json.dump(object.to_struct(), file, indent=4)
