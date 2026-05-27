# osu!importer whatever this is

basically doing whatever the name implies

## Installation

pip install PyQt5 requests | wont work without these two

all three .py have to be downloaded in the same dir

## Setup

**Cookie** — go to F12 browser dev tool > Storage | name: `osu_session` | value: `"your cookie"`, idk if this have time limit, figure it out yourself

**Client Secret** — go to your osu.ppy.sh account setting, OAuth: New OAuth Application, give it a name or sum, leave callback URLs empty, register and done
- your secret is the hidden long ahh one
- can you get hacked? yes, your CPU driver mosfet will explode, figure that out yourself, not my problem

## Download Servers

by default it'll use ppy.sh official server, but will try to use mirror if unavailable:

| Server | Docs |
|---|---|
| `nerinyan.moe` | https://github.com/Nerinyan/Nerinyan-WEB |
| `catboy.best` | https://catboy.best/docs |
| `txy1.sayobot.cn` | idk man, claude told me it work so... |

## Why?

cuz i want one of my proof of history to not delete itself in case my SSD died, osu song lib can be so massive it made its own gravitational pull

as long as you got your beatmap IDs you can recover thousands and thousands of individual beatmap sets

and replays /r is important aswell, dont forget to back it up to cloud or something

this process is slow, depends on where your ISP decide to route its server and your baseline internet connection speed, osu.ppy.sh is slow by nature
