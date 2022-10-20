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