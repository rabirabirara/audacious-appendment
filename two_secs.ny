;nyquist plug-in
;version 1
;type generate
;name "Surround silence"
;action "Processing..."
;author "Spencer Gouw"
;copyright "Released under terms of the GNU General Public License version 2"
;literally copied from Steve Daulton's "Insert Silence"

(defun insertstart (sig) 
  (sim (s-rest 0) 
    (at 1 (cue sig))))
(multichan-expand #'insertstart s)


;multichan-expand is defined in nyquist.lsp in Audacity's Nyquist folder.
;It's a quick way to work with stereo, since Nyquist can actually
;only operate on mono channels.
;Stereo channels are passed as arrays of mono channels, with each element
;of equal length; the function is called once for each.



;see snd-add, shift-time, etc.
;recommended to not use snd- functions, as those are low level
;use higher level functions instead

;also read about environment variables. like what is *loud* and *warp*?
