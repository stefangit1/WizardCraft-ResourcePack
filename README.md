# WizardCraft Resource Pack

Textures and models for the WizardCraft server: items (wands, armor, spell icons) and changed creatures.
This repository must be **public**: players download the pack from GitHub when they join.

## Folders

```
pack/                           everything in here ends up in the pack
  pack.mcmeta                   pack description and Minecraft version (min_format/max_format 88 = Minecraft 26.2)
  pack.png                      icon in the client's pack list
  assets/wizardcraft/           our namespace, the same name the plugin uses for its items
    items/<path>.json           which model an item shows (item_model component)
    models/item/<path>.json     the model itself
    textures/item/<path>.png    the texture
  assets/minecraft/...          replaces vanilla textures, e.g. textures/entity/zombie/zombie.png for a creature
tools/build_pack.py             builds and checks the zip (the workflow and you run the same script)
```

## Adding an item

The plugin gives an item the model `wizardcraft:<path>`, for example the Diffindo icon uses
`wizardcraft:spell/diffindo`. For that name the pack needs three files (copy the Diffindo ones):

1. `assets/wizardcraft/items/spell/diffindo.json`: points to the model
2. `assets/wizardcraft/models/item/spell/diffindo.json`: points to the texture
3. `assets/wizardcraft/textures/item/spell/diffindo.png`: the image

`tools/build_pack.py` checks that every model and texture a file points to exists, so a typo fails the build and not the game.
The Diffindo texture is only a placeholder.

## From a change to the server

| You push to | Pack goes to |
|---|---|
| `main` | all `hogwarts-N` |
| `testserver-N` | only the test server `testserver-N` |

1. The workflow builds the pack and publishes it in the release `pack-<branch>` together with `manifest.json`.
2. The servers look at the manifest of their branch every minute. A new pack goes to all online players within about
   a minute, without a server restart, and to everyone who joins later.
3. A test server whose branch has no pack yet uses the pack of `main`.
4. `/wizardcraft pack` on a server shows which pack it offers, `/wizardcraft pack reload` checks right away.

The first push of a new branch without a change in `pack/` starts no build. Start it by hand under Actions, Run workflow.

## Trying it locally

```
python3 tools/build_pack.py
```

writes `build/WizardCraft-Pack-<hash>.zip`. Put it in `.minecraft/resourcepacks` to look at the textures without a server.

## One-time setup of this repository

1. Create the public repository `stefangit1/WizardCraft-ResourcePack` and push `main`
   (another name works too: `resourcepack.repository` in the plugin's `config.yml`).
2. Nothing else: the workflow uses the built-in token of GitHub Actions and runs on GitHub's own runners.
