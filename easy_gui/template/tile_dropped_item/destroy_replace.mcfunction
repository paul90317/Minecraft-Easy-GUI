summon item ~ ~-1 ~ {Tags:[egno,egset],CustomNameVisible:1b,CustomName:'{"text":"<text>","italic":false<color>}',Motion:[0.0,0.3,0.0],Item:{Count:1b,id:"<item>",tag:{display:{Name:'{"text":"<text>","italic":false<color>}'},eg:{is:1b,type:tile,name:<id>}<enchant><tag>}}}
<load>
kill @s
execute positioned ~ ~-1 ~ run tag @e[sort=nearest,limit=1,type=item,tag=egset] remove egset
setblock ~ ~-1 ~ air replace