# audacious-appendment
An Audacity script to merge a series of mp3 tracks into one, and perform some minor effects.

## Usage
Say you have a series of tracks, e.g. the three movements of a concerto.  You want to merge them into one track.

Run the script on the three movements, and if you want, truncate the silence of their tracks (to be fully implemented); and if you want, determine where to add silence and how much to add.
The script will do it all in Audacity, using Audacity commands and a few Nyquist commands (no worries, no plug-ins required, luckily).  (Sorting hasn't been implemented yet, so the order of the tracks should rely on the
order of arguments passed in.)

`./script.py "medtner 1.mp3" "medtner 2.mp3" "medtner 3.mp3" -o mechamedtner.mp3`

## Functionality
The script is very basic at present.  It should:

1. Read files pass as arguments, determine their path, and create a .lof file from them
2. Open Audacity, and import the .lof file
3. Merge the tracks together, end to end
4. Add some effects, such as amplification or truncate-silence
5. Export the result to a path

## Future

There is much to be added.  I want to add a sort option for files that are named in a sortable way (classical music).  I want greater options for adding silence to the start/end of tracks.  I want to make the script nicer.  I want to add incremental track addition, so that I can merge more 
than a dozen tracks together (Audacity's track limit is 16; if I want to combine several tracks a la some Vikingur Olafsson album, then I need to implement this).  I need to add Linux/Mac support,
for no reason but robustness.  Also, the script doesn't work if this instance of Audacity's pipes had already been used earlier.

Audacity's capabilities are also limited.  If we could specify durations on commands, it would be great and extremely convenient.  If we could control export options, it would be extremely
great.  If Python could have a better argparse module, that would be excellent.


## Nyquist Commands
The Nyquist-LiSP commands were a pain to write.  The documentation is austere; the community is nonexistent (obviously); none of the symbol names make ANY intuitive sense (classic functional programming style).

And of course, s-expressions are just ugly, if you haven't written LiSP or read the oh so revered book on the structure and interpretation...  But hey, s-expr parsers are so easy to write, aren't they?

The capabilities of Audacity's scripting API is itself still somewhat immature, but luckily it turned out to have everything I needed to write what I wanted.  There were a lot of times
I had thought I was stuck - for example, I relied on the Generate: Silence effect in the GUI, but it was not available in the scripting API.  I eventually decided to just make noise with an amplitude of 0. But while this would work in the GUI, I found out I couldn't specify a _duration_ from the script! - and so my quest to study elementary Nyquist at 3:30 AM kicked off.  And even when I found something that worked when I entered it into the Nyquist prompt in the GUI, it didn't work in the script!  Turns out it wouldn't work for multiline strings; so I took advantage of s-expr's lack of needed whitespace and put it all in a one-line string.

```Lisp
; Example of a Nyquist comamnd that inserts silence at the beginning of a selection.
(defun insertstart (sig) 
  (sum (s-rest 2) 
    (at 1 (cue sig)))) 
(multichan-expand #'insertstart s)
```

Audacity defines multichan-expand for use with stereo channels, since Nyquist can only apply functions to one channel at a time (and represents stereo as arrays of channels).

Actually, to make this add silence to the end of a selection instead, it's as easy as changing the (at 1) to (at 0).

Overall, you can imagine this command to say something like: define a function "insertstart" that takes a signal (a sound) and gives the sum of some silence and the signal but shifted over by its duration.  Then call the function on both channels.  Gosh, Lisp is cool and ugly at the same time.  I much prefer ML; but I respect LiSP all the same.

Hopefully, if anyone ever has the problem of inserting silence at the beginning and end of a file, they can look at my script and figure it out themselves.
