# NOT WORKING BRANCH. 
This is postponed refactoring toward new config and py3.
No time to finish it now. If you would like to pick it up
contact me and I'll try answer questions.

## Toward Terminator2 (from Terminator 1.91)

This repo contains Terminator in my (ohir's) version. It is based on v1.91 python2 release. 

---
#### Title bar conveys more info now:
![New features visible in terminal's title bar](../site/pics/terminator1.92_titlebar.png)
![New features visible in local menu](../site/pics/terminator1.92_lmenu.png)

---
#### Title bar indicators can be hidden, new terminals can be cloned or templated:
![New features to be configured in Preferences.General](../site/pics/terminator1.92_generaltip.png)

---
#### Many things can now be configured per terminal basis:
![New features to be configured per terminal in Preferences.Layouts](../site/pics/terminator1.92_layouts.png)

---
### Changelog for terminator 1.92.0:

#### new features
    * terminals can start in a fixed cwd (configurable per terminal)
    * terminals can have their own history (configurable per terminal)
    * terminals can load their own environment (configurable per terminal)
    * terminal can execute a command on the start (configurable per terminal)
    * terminal can prefill a command on the start (to be run by the user later)
    * new tab is always opened right to the current one
    * new terminals can take settings from a configurable template, or
    * new terminals can take settings from the current one (be a clone of)
    * cloned terminals have title and caption strings appended with '.new'
    * cloned terminals are not permanent (not saved in the config) until manual save
    * local menu allows for manual save that saves also '.new' terminals
    * titlebar is now a main source of information for the terminal, with 
      name of the loaded environment and a tab caption added. It allows one
      to work without GUI tabs. Titlebar is now shown by default.

#### enhancements
    * Notebook is now named to allow easy .css fixes (for the tabbar)
    * Prefseditor shows tooltips for new feature items 

####  bug fixes
    * Tabs restore as saved (in proper order)
    * Spanned terminals restore as saved (in proper places)
    * Label edits (tab captions and titlebar) from GUI make to the config and vice-versa
    * GTK layout files do not produce GTK warnings (old gtk-related code still does, in some places)

#### whats broken

  - Plugins that read parent config may break due to the configfile keys changed.
  - Multiwindow layouts were NOT tested at all
  - manpages do not reflect option changes.

#### whats deprecated

  - Terminator 1.92.0 supports many layouts only via separate config files (-g config).
    > The very concept that code must close terminals then reopens anew from other portion
    > of the giant config is alien to me (ohir). This code is disabled now and will be removed.
  - Panic key, aka hide window is disabled and will be removed. This is brittle code that does
    not work as intended on most but gnome based window managers.
    > Use your wm keybindings to manage window state, if you really need a panic key.
  - Group-related shortcuts are removed from the default keybindings.
    Groups and input cloning makes sense for a tiny fraction of power users only.
    Ones that already know how to confingure then use keyboard driven groups. 

#### roadmap (TODO for the future maintainer)

  - [ ] remove window hidding code
  - [ ] make -l option take short name to be expanded as $CONFIG_DIR/name.layout
  - [ ] remove layouts list from the preferences window
  - [ ] remove configobj dependency: make python3 config base first, then
        port whole terminator to python3.
  - [ ] Add either profile chooser to the local menu
  - [ ] or make per terminal preferences accessible from the local menu.

### appearance fix

For most new distros GTK3 defaults are wrong for terminal window use. The `Clearlooks`
theme directory contains app specific css you can use to fix GTK/desktop theme you use.

### why github fork?

Launchpad walls developers. Last time I tried to create a launchpad account
Cannonical tried to force on me their CoC. Then I would have to wait for being
accepted as a "team member" to be able to post to the development list. Farewell then.
Also, development there stalled in year 2017.

### semantic versions

While refactoring of terminator is far from the finish, I would like to
avoid labelling it 'alpha' or 'beta'. _In this repo I use semantic versioning
tags, with a stage denoted below:_

  - **1.92.0** enhanced from 1.91 upstream fork. Python 2.7.

Ohir Ripe

---
## INSTALL TL;DR

UNINSTALL old terminator if you used v1.91 from your distro packages!
open an other terminal emulator or open console, then:

```bash
    # FIRST:  export release name and terminator's default config directory:

    export tVER="1.92.0"           # change numbers to match latest release!
    export tREL="terminator-$tVER" # use release

    export tmCF="$HOME/.config/terminator" # DO IT! commands below use it
    mkdir -p $tmCF/                        # directory may already exist

    cd ~/Downloads                         # or to an other directory

    # download release tarball:

    wget -O $tREL.tar.gz https://github.com/ohir/terminator/archive/$tVER.tar.gz

    # Now copy&paste, then run commands line by line - observing any error messages:

    tar -zxf $tREL.tar.gz && cd $tREL
    ./setup.py install --prefix=$HOME/.local --record=$tmCF/uninstall.list
    mv setup.py $tmCF/
    echo "cd $tmCF/ && ./setup.py uninstall --manifest=uninstall.list"> $tmCF/uninstall
    cp INSTALL $tmCF/README
    sudo ln -s $HOME/.local/bin/terminator /usr/bin/terminator
    
    # now try to run terminator from the current terminal - observing any error messages:

    $HOME/.local/bin/terminator

    # if it does not run, read error messages and install libraries reported as lacking.
    # first try to install them from your distro repositories, pip install if you must.
    # rinse and repeat till terminator runs
    # if it runs — you're done. Cleanup:
    cd ..
    if [ -d $tREL ]; then rm -rf $tREL; fi

    # now Terminator should be available form your GUI Accesories menu
```

## UNINSTALL TL;DR:
```bash
source $HOME/.config/terminator/uninstall
```

---
> This is a README.md for the github repo page.
> You should read also package README (without md).

