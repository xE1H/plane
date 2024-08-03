import flask
import sigqual
import requests
from xml.dom import minidom

app = flask.Flask(__name__)


@app.route('/signal_quality')
def signal_quality():
    sq = requests.get('http://192.168.8.1/api/device/signal').text
    xmldoc = minidom.parseString(sq)
    itemlist = xmldoc.getElementsByTagName('rssi')
    rssi = int(itemlist[0].firstChild.nodeValue)
    itemlist = xmldoc.getElementsByTagName('rsrq')
    rsrq = int(itemlist[0].firstChild.nodeValue)
    itemlist = xmldoc.getElementsByTagName('rsrp')
    rsrp = int(itemlist[0].firstChild.nodeValue)

    return sigqual.calculate_signal_quality(rssi, rsrq, rsrp)


if __name__ == '__main__':
    app.run()
