import requests
import re
import bs4
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

currtime = datetime.utcnow()  # format: datetime.datetime(2018, 10, 27, 18, 42, 5, 759638)
day = currtime.day  # should return today's day 27
month = currtime.month  # should return 10
year = currtime.year - 2000  # should return 18

base_url = "http://www.lib.berkeley.edu/hours"
#url = 'http://www.lib.berkeley.edu/hours/?libraries%5Bid%5D%5B%5D=&commit=Go&day=' + '11' + '%2F' + '4' + '%2F' + str(year)
url = 'http://www.lib.berkeley.edu/hours/?libraries%5Bid%5D%5B%5D=&commit=Go&day=' + str(month) + '%2F' + str(
    day) + '%2F' + str(year)
myurls = []
hours_regex = "(?:[1-9][0-2]?(?::[0-9]{2})? ?(?:am|pm|noon|midnight))|closed|24 hours"
data = requests.get(url)
soup = BeautifulSoup(data.text, 'html.parser')
libs = soup.find_all('div', class_="library-info-block")
libnames = []


# Collect all the names of the 37 libraries, put them in LIST libnames
def all_names():
    for lib in libs:
        name = lib.find('h2', class_="library-name-block").find('a').contents
        if len(name) == 1:
            # print(name)
            libnames.append(name[0])
        else:
            concat_name = str(name[0]) + str(name[len(name) - 1])
            # print(concat_name)
            libnames.append(concat_name)


def get_days():
    # create a list of URLs for every day of the week by changing the time parameters 
    # return a list of URLs
    urls = []
    for i in range(1, 7):
        next_date = currtime + timedelta(days=i)
        url = 'http://www.lib.berkeley.edu/hours/?libraries%5Bid%5D%5B%5D=&commit=Go&day={}%2F{}%2F{}'.format(
            next_date.month, next_date.day, next_date.year - 2000)
        urls.append(url)
    return urls


class Library:
    def __init__(self, name):
        self._name = name
        self._phones = set()
        self._opentime = []
        self._closetime = []
        self._image = ""

    # find the entire chunk of data belonging to self, store in SELF._INFO
    def getallinfo(self):
        var = self._name
        order = libnames.index(var)
        self._info = libs[order]

    def get_main_page(self):
        url = self._info.find('h2', class_="library-name-block").find('a')['href']
        data = requests.get(url)
        self._mainpage = BeautifulSoup(data.text, "html.parser")

    def get_about(self):
        if self._name == "Moffitt Library":
            self._about = "Moffitt Library, located next to Memorial Glade, is one of the busiest campus libraries with " \
                          "undergraduate course reserves, computer lab, makerspace, media center, copy center, campus classrooms," \
                          "and convenient access to the research collections in the Main (Gardner) Stacks.  Moffitt floors 4 & 5, " \
                          "accessed through the east entrance are open 24 hours during the fall and spring semester " \
                          "and are snack and drink friendly. Reserved for UC Berkeley students and faculty, Moffitt serves " \
                          "students of all majors and is open the longest hours.  Campus visitors are welcome at the " \
                          "Free Speech Movement (FSM) Café and popular Newspaper Display Wall near the 3rd floor south entrance."
        else:
            try:
                about = self._mainpage.find(["h1", "h2", "h3", "h4", "h5", "h6"],
                                            text=re.compile("(?:[Aa]bout|Mark Twain Papers)"))
                self._about = about.findNext("p").text
            except:
                self._about = ""

    # Find the phone number contained in SELF._INFO
    def findphone(self):
        tags = self._mainpage.findAll("div", {
            "class": ["views-field-field-banc-phone-number", "views-field-field-phone-number"]})
        for tag in tags:
            phones = re.split("[^0-9-() ]", tag.find("div").text)
            for phone in phones:
                stripped = re.sub("[^0-9]", "", phone)
                if stripped:
                    self._phones.add(stripped)

        if not self._phones:  # if unsuccessful, try approach 2
            phone = self._info.find('div', class_="library-phone-block").find("p").text
            self._phones.add(re.sub("[^0-9]", "", phone))

            # Find the time range during which the lib is open.

    # Possible formats: 3am-4pm; 4:30am-10pm; "Closed"; 1pm-5pm By Appointment Only; multiple time slots
    # Store the range in SELF._TIME_RANGE
    def findtimerange(self):
        if self._name == "CED Visual Resources Center":
            self._opentime = [-1, ["09:00", "13:00"], ["09:00", "13:00"], ["09:00", "13:00"], ["09:00", "13:00"],
                              ["09:00", "13:00"], -1]
            self._closetime = [-1, ["12:00", "17:00"], ["12:00", "17:00"], ["12:00", "17:00"], ["12:00", "17:00"],
                               ["12:00", "17:00"], -1]

        else:
            raw_times = self._info.find('div', class_="library-hours-block").text.strip()
            cleaned = raw_times.lower().replace("noon", "pm").replace("midnight", "am")
            self._time_range = re.findall(hours_regex, cleaned)

    # Parse time range for either open or close time, depending on if open_time is True or False
    def parse_time_CED(self):
        if self._name == "CED Visual Resources Center":
            self._opentime = [-1, ["09:00", "13:00"], ["09:00", "13:00"], ["09:00", "13:00"], ["09:00", "13:00"],
                              ["09:00", "13:00"], -1]
            self._closetime = [-1, ["12:00", "17:00"], ["12:00", "17:00"], ["12:00", "17:00"], ["12:00", "17:00"],
                               ["12:00", "17:00"], -1]

   
    def parse_time(self, open_time=True):
        if self._name != "CED Visual Resources Center":
            if not self._time_range:  # Edge cases
                return -1
            elif len(self._time_range) == 1 and open_time == False:
                return -1

            parse_time = self._time_range[0] if open_time else self._time_range[1]

            if parse_time == "closed":
                return -1
            elif parse_time == "24 hours":
                return "0:00" if open_time else "23:59"
            elif ":" in parse_time:
                return datetime.strftime(datetime.strptime(parse_time, "%I:%M %p"), "%H:%M")
            else:
                return datetime.strftime(datetime.strptime(parse_time, "%I %p"), "%H:%M")

    def findopentime(self):
        if self._name != "CED Visual Resources Center":
            self._opentime.append(self.parse_time(open_time=True))

    def findclosetime(self):
        if self._name != "CED Visual Resources Center":
            self._closetime.append(self.parse_time(open_time=False))

    # def getlocation(self):
    #     location = geolocator.geocode(self._name)
    #     if location and "Berkeley" in location.address:  # ensure we have a positive result
    #         self._address = location.address
    #         self._latitude = location.latitude
    #         self._longtitude = location.longitude
    #     else:
    #         addr = self._mainpage.find("div", class_="views-field-field-campus-address")
    #         if addr:
    #             children = list(addr.find("p").children)
    #             self._address = " ".join([child for child in children if isinstance(child, bs4.NavigableString)])
    #         else:
    #             self._address = ""
    #         self._latitude = -1
    #         self._longtitude = -1

    # If CURRTIME is between _OPENTIME & _CLOSETIME, return True. Else False
    def isOpen(self):
        if self._name != "CED Visual Resources Center":
            print(self._opentime[0])
            print(self._closetime[0])
            if self._closetime[0] == -1 and self._opentime[0] == -1:
                return False
            if self._opentime[0] == -1 and self._closetime[0] != -1:
                curr_time = datetime.utcnow()
                close_time = datetime.strptime(self._closetime[0], "%H:%M")
                return curr_time < close_time
            if self._opentime[0] != -1 and self._closetime[0] == -1:
                return True

            else:
                curr_time = datetime.utcnow()
                print(self._opentime[0])
                print(self._closetime[0])
                open_time = datetime.strptime(self._opentime[0], "%H:%M")
                close_time = datetime.strptime(self._closetime[0], "%H:%M")
                return open_time < curr_time and close_time > curr_time
        else:
            if self._closetime[0] == -1 and self._opentime[0] == -1:
                return False
            else:
                curr_time = datetime.utcnow()
                week_day = datetime.today().weekday()
                today_open_time = self._opentime[week_day]
                today_close_time = self._closetime[week_day]

                open_time1 = datetime.strptime(today_open_time[0], "%H:%M")
                open_time2 = datetime.strptime(today_open_time[1], "%H:%M")
                close_time1 = datetime.strptime(today_close_time[0], "%H:%M")
                close_time2 = datetime.strptime(today_close_time[1], "%H:%M")

                return (open_time1 < curr_time and currtime < close_time1) or (
                        open_time2 < curr_time and currtime < close_time2)

    def serialize(self):
        values = {}
        values['name'] = self._name
        values['phone'] = list(self._phones)
        values['picture'] = self._image
        values['description'] = self._about
        #values['address'] = self._address
        #values['latitude'] = self._latitude
        #values['longitude'] = self._longtitude
        values['is_open'] = self.isOpen()
        values['open'] = self._opentime
        values['close'] = self._closetime

        return values

    def getimage(self):
        image_block = self._mainpage.find("div", {"class": re.compile("field-location-image")})
        if not image_block:
            all_libs = soup.findAll('div', class_="closed")
            for div in all_libs:
                name = div.find('div', class_='library-info-block').find('h2', class_="library-name-block").find(
                    'a').text
                if name == self._name:
                    imgsrc = div.find('div', class_='library-image-block').find('img')
                    self._image = base_url + imgsrc['src']
                else:
                    continue
        else:
            self._image = image_block.find("img")['src']


if __name__ == '__main__':
    all_names()
    for lib in libnames:
        library = Library(lib)
        library.getallinfo()
        library.get_main_page()
        library.get_about()
        library.findphone()
        library.getimage()
        #library.getlocation()

        library.parse_time_CED()
        #library.isOpen_CED()
        library.findtimerange()
        library.findopentime()
        library.findclosetime()


        for day in get_days():  # 1 to 6 days out
            new_data = requests.get(day)
            day_soup = BeautifulSoup(new_data.text, 'html.parser')
            library._info = day_soup.findAll('div', class_="library-info-block")[libnames.index(library._name)]

            library.findtimerange()
            library.findopentime()
            library.findclosetime()

        with open("{}.json".format(library._name.replace("/", "-")), "w") as f:
            json.dump(library.serialize(), f)

        # mof = Library("Moffitt Library")
        # mof.getallinfo()
        # mof.findtimerange()
        # mof.findopentime()
        # mof.findclosetime()
        # mof.isOpen()
        # print(mof._opentime)
        # print(mof._closetime)