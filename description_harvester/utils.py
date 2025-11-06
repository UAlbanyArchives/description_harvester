import re
import os
import time
import json
from pathlib import Path
from hashlib import md5
from jsonmodels.errors import ValidationError
from description_harvester.models.description import Component

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

# Caching to disk functionality

def write2disk(object, collection_id):
	# takes a jsonmodel object and writes it to disk for testing

	test_path = Path.home() / ".description_harvester"
	test_path.mkdir(parents=True, exist_ok=True)
	out_path = test_path / f"{collection_id}.json"

	with open(out_path, "w", encoding='utf-8') as file:
		json.dump(object.to_dict(), file, indent=4)

def get_cache_key(identifier):
    # Handles special characters and URIs cleanly
    return md5(str(identifier).encode()).hexdigest() + ".json"

def component_from_dict(data):
    """
    Recursively rebuild a Component instance (and its nested children) from a dict.
    """
    # First create the base Component without components
    components_data = data.pop('components', [])
    component = Component(**data)

    # Now recursively load any nested components
    for child in components_data:
        component.components.append(component_from_dict(child))

    return component

def save_to_cache(identifier, data, cache_dir):
    """
    Save the given jsonmodel data to a cache file.
    """
    key = get_cache_key(identifier)
    
    # Convert `data` (a jsonmodel object) to a dictionary using `to_dict()`
    if hasattr(data, 'to_dict'):
        data = data.to_dict()  # Convert the jsonmodel object to a dictionary
    
    if cache_dir:
        # Expand ~ if present and ensure the cache directory exists
        cache_dir = Path(cache_dir).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the data along with a timestamp
        with open(cache_dir / key, "w", encoding='utf-8') as f:
            json.dump({
                "timestamp": int(time.time()),
                "data": data
            }, f)

def load_from_cache(identifier, cache_dir, max_age_seconds=86400):
    key = get_cache_key(identifier)
    if cache_dir:
        cache_dir = Path(cache_dir).expanduser()
        path = cache_dir / key
        
        if path.exists():
            with open(path, "r", encoding='utf-8') as f:
                cached = json.load(f)
                age = time.time() - cached["timestamp"]
                if age < max_age_seconds:
                    try:
                        print (f"\tReading from cache: {path}")
                        return component_from_dict(cached["data"])
                    except Exception as e:
                        print(f"\tError rebuilding model: {e}")
                        return None
        return None
