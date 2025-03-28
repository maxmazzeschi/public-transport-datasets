# public_transport_datasets

A Python package that provides public transport datasets for multiple cities.

Please refer to [Report.md](https://github.com/maxmazzeschi/public-transport-datasets/blob/main/Report.md) for Countries and Cities supported

## Adopt a City or a Country !
Can't find your City or Country? Or information are incomplete or not exact ?
I will be happy for your contribution!  
Send me a message with details for the feed, or with the city and the transportation provider, and I'll try to add to the datasets!

## About API Keys

Some providers require api key to access their realtime data.

Check the column *ENV VAR for API KEY* and *Issued by* in the [Report.md](https://github.com/maxmazzeschi/public-transport-datasets/blob/main/Report.md).

Library expects an environment variable with the value of your personal key to allow access their data


## Installation

You can install the package via pip:
```
pip install public_transport_datasets
```

## How to use
There is a simple webapp available on Github [bus-and-go](https://github.com/maxmazzeschi/bus-and-go) that uses the datasets, plotting data on a map.


It's available at [https://bus-and-go.onrender.com/](https://bus-and-go.onrender.com/)
 
## To Do

- Add more sources and refine the existing ones

- Support SIRI standard (wip)

- Support TFL standard (wip)

- AOB

## Credits

Most of the feeds information have been taken from [www.mobilitydatabase.org](http://www.mobilitydatabase.org)
