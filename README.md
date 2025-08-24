This tool exists to create images for custom cards, as you would find in the game "Library of Ruina".
I am a huge fan of this game, and I was suprised no such automatic tool existed!
For accessibility, I considered making this a browser-based tool, but the usage of a Photoshop template made it a bit awkward.

# Setup

First, you must have a working Python3 installed.
If you don't know how to do that, [here](https://www.python.org/downloads/) is a good place to start.

If you already have git, then `git clone` this repository.
Otherwise, just click the download button and unzip the archive it downloads.

Finally, open a terminal with a working directory in the unzipped folder.
If you are on Windows and don't know how to do this, try:
- Navigating to the folder
- Shift + Right Click
- Open Command Window Here

Install the proper Python3 modules via either:
- `python3 -m pip install -r requirements.txt`
- `pip3 install -r requirements.txt`

**You may also need to install the fonts in `assets/fonts`**.
On linux, this was a simple `cp -r assets/fonts/* /usr/local/share/fonts`.
Certainly the process is different on Windows (perhaps try clicking the files in that folder and seeing what prompts you).

# Running

With a terminal open with a working directory in this project's folder, try `python3 bin/generate_card.py --help`.

Example command to make a card: `python3 data/test/degraded_shockwave.json degraded_shockwave.png`.
This command will create the `degraded_shockwave.png` file in your current folder.

Breakdown of other possibilities:
- Adding a `-m` to the command will create a "mini" of the card instead (be sure to save it to a different file name)
- If you are in a different working directory (or have a lot of custom stuff), then you can clarify where to find assets with `-a`, e.g. `-a /home/ironraptor3/assets`
- If you would like to extend or alter the keywords available (see below), then you can specify a new keyword file with `-k` e.g. `-k assets/custom/keywords.json`

# Making a new card

Cards can be defined in the JSON format.
See a card in `data/test/` for an example.
You can create your own cards in `data/`.

Format:
- parent: if defined, inherits from another card. See `data/test/prepared_mind_lulu.json` for an example. This is specified as a **relative** path from this json file.
- name: Name of the card
- cost: Light cost of the card
- type: One of ["melee", "ranged", "instant", "mass"]
- rarity: One of ["paperback", "hardcover", "limited", "objet d'art", "e.g.o"]
- grit: **experimental, only looks good with the `-m` option** Either `true` or `false`. If false, removes the grimy look typically on cards
- art: **relative** path to the image to use in the card
- preamble: The header text of the the card, if any
- dice: A JSON list, containing objects with:
    - type: One of ["slash", "pierce", "blunt", "block", "evade", "slash\_counter", "pierce\_counter", "blunt\_counter", "block\_counter", "evade\_counter"]
    - range: **text** for the roll range of the dice
    - effect: optional, the effect text.

For the preamble and dice, one can specify defined keywords by typing e.g. `{burn}` for the Burn keyword.
See a list of the default keywords in `assets/keywords.json`.
You can create custom keywords, see the Customization section below.

# Customizing

Like with cards, you can define your own, custom `keywords.json` file.
See `assets/keywords.json` for an example of what you can do.

Format:
- parent: if defined, refers to a parent keywords file. This is very useful if you would like to just make an addition to the keywords file or overwrite a keyword while keeping the rest the same. As before, this is a **relative** path to the parent file. If you had a keywords file in `assets/custom/keywords_custom.json` and want the parent `assets/keywords.json`, then specify `../keywords.json` 
- keyword
    - text
        - content: The replacement text for this keyword, comes after images. It can end with a `\n`, which will insert a newline. If you just need a newline anywhere, try the `{br}` keyword, which is just an `\n`
        - color: If specified, this is the color the text should be. If unspecified, the keyword is the traditional yellow.
    - image
        - path: A relative path to the icon to embed in the text
        - convert\_color: `true` or `false`. If `true`, recolors the image red for offense, blue for defense, or white for preamble depending on where the image is being drawn.

# Automating

You may notice the `Makefile` and the `make_all.sh`.
If you know how to run make commands, you can instead use something like:
`make output/test/degraded_shockwave.png` and if `data/test/degraded_shockwave.json` exists and has been edited since last making the image, it will be recreated.
Relevant environment variables:
- ASSET\_PATH
- KEYWORD\_PATH

This is **not** a fully smart process though.
Should you make changes to the images or keywords a card uses, it won't be regenerated without first deleting the file (these are not a dependency).
You COULD make custom dependencies for your cards though, and then it would be regenerated if you updated images or keywords.

The shell script `./make_all.sh` builds everything in `data` into a corresponding full and mini in `output`

# Concepts / Thought Process

I wanted to make some custom cards for a tabletop campaign I am interested in running, hence the dice icons I made.
I understand they aren't the BEST looking in the world, feel free to replace them.
I used Google dice roller for the inspiration on how to draw and shade each of them.

This approach uses a Photoshop template (see Acknowledegments below) that was created for making custom cards.
There were MANY custom cards that I wanted to make, and I wanted a way of automating the process (and I would annoy myself at making the spacing perfect by hand).
I wanted a standalone tool which did not require the use of Library of Ruina / modding as a surrogate.
Moreover, I did not want to pay for Photoshop (or prompt others to pay for it).
I'm sure its a great tool, but I certainly don't need a subscription to it.
I first inspected the the `.psd` file by using [Photopea](www.photopea.com).
Ultimately (after a lot of experimenting), I decided to just use a Python library which could automate some simple `.psd` file stuff (as there is allegedely a Python library of everything).

I went with a "parenting" system for the cards in case there were cards with a lot of similarities but I wanted to use a different picture or a slightly different preamble.
The "Prepared Mind" cards were certainly in my thoughts when doing this.

Ultimately, I thought "why not add some special custom features if I am making an entire tool anyway".
This is how I arrived at embedding some icons in the text, Limbus Company style.

# Acknowledgements

From [tiphereth](tiphereth.zasz.su) and ultimately "Library of Ruina":
- various test images:
  - `data/test/prepared_mind_lulu.jpg`
    - `data/test/prepared_mind_mars.jpg`
    - `data/test/degraded_shockwave.jpg`
    - `data/test/repressed_flesh.jpg`

From the [Limbus Wiki](limbuscompany.wiki.gg) and ultimately "Limbus Company":
- various test images:
  - `data/test/cinq_east_donquixote.png`
    - `data/test/rosespanner_meursault_ut.png`
    - `data/test/sunshower_heathcliff_ut.png`
- all of the icons in the `assets/limbus` folder, used for status effects in text

From [This Google Drive Link](https://drive.google.com/drive/folders/12k2d_mPNzK6UfwFJcekXIiy3d1pJallO), and ultimately "Library of Ruina":
- I believe this is by the reddit user `u/Macrosis2020`. **Thank you so much** for your hard work and giving me a starting point!
- fonts:
  - all fonts in the `assets/fonts` folder
  - the photoshop `.psd` file:
    - `assets/lor_template.psd`
  - the grit for displaying over the light cost of a card
    - `assets/cost_grit`
  - the various dice icons in
    - `assets/ruina`

Inspiration, in part by [This prototypical tool](https://github.com/Stiggu/LoR-Card-Generator/tree/master)

# Support

If you'd like to support me, I have a [Ko-Fi](https://ko-fi.com/ironraptor3)

