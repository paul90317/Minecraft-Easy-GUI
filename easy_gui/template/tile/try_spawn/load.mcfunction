setblock ~ ~ ~ <block>{CustomName:'<text>'} destroy
summon glow_item_frame ~ ~ ~ {CustomName:'<text>',Tags:[eg.<id>,egset],Facing:1b,Item:{id:"<item>",Count:1b,tag:{<tag>}},Invulnerable:1b,Fixed:1b,Invisible:1b}
<load>
kill @s
tag @e[sort=nearest,limit=1,type=glow_item_frame,tag=egset] remove egset
