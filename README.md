# osu!importer whatever this is

basically doing whatever the name implies, read song folder and make index(list of IDs), download beatmap-set from that index, mostly used later - for in case you want to redownload everything etc, it wont overwrite your existing folder by default, or you can choose to save the newly downloaded beatmap to a specific directory

## Installation 
*- tested using recent version of Python 3.9.13*
```bash
pip install PyQt5 requests 
```
package needed: PyQt5 and requests, wont work without these two

all three .py have to be downloaded in the same dir side by side

## Setup

**start osu_importer.py with terminal pointing to the .py file directory**
*for example:*
```bash
cd path/to/osu_importer
python osu_Importer.py
```
- or type "CMD" inside of address/path bar on windows file explorer to cd directly to that path
<img width="452" height="158" alt="image" src="https://github.com/user-attachments/assets/02766133-64b4-4044-a05f-eef041770e8e" />

- this insures you can read and catch any error code if it crashes etc
  
**Cookie** — go to F12 browser dev tool > Storage | name: `osu_session` | value: `"your cookie"`, idk if this have time limit?

**Client Secret** — go to your osu.ppy.sh account setting, OAuth: New OAuth Application, give it a name or sum, leave callback URLs empty, register and done
- your secret is the hidden long ahh one
- can you get hacked? yes, your CPU driver mosfet will explode, figure that out yourself or read the source code, *just make sure you dont just post your osu! account client code publicly*
  
## Download Servers

by default it'll use ppy.sh official server, but will try to use mirror if ppy.sh is unavailable:

| Server | Docs |
|---|---|
| `nerinyan.moe` | https://github.com/Nerinyan/Nerinyan-WEB |
| `catboy.best` | https://catboy.best/docs |
| `txy1.sayobot.cn` | idk man, claude told me it work so... |

## limitation

- untested replay tab
- unknown beatmap, self made, or beatmap who have DCMA flag will be unavailable do to various reason but mostly it just doesn't exist in the server
- im a total rookie to programming, it work on my machine so...
  
## Why?

cuz i want one of my proof of history to not delete itself in case my SSD died, osu song lib can be so massive it made its own gravitational pull

as long as you got your beatmap IDs you can recover thousands and thousands of individual beatmap sets

and replays /r is important aswell, dont forget to back it up to cloud or something

this process is slow, depends on where your ISP decide to route its server and your baseline internet connection speed, osu.ppy.sh is slow by nature
