"""Generate original, local SVG illustrations; no external image service is needed."""
from pathlib import Path
import math

OUT = Path(__file__).resolve().parent.parent / 'static' / 'art'
OUT.mkdir(parents=True, exist_ok=True)

def svg(body, bg='#e6ebda', view='0 0 600 350'):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}"><defs><filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="9" stdDeviation="9" flood-color="#233c2d" flood-opacity=".13"/></filter><radialGradient id="plate"><stop stop-color="#fffef5"/><stop offset=".8" stop-color="#f5f2df"/><stop offset="1" stop-color="#dedcc7"/></radialGradient></defs><rect width="600" height="400" fill="{bg}"/>{body}</svg>'''

def plate(cx=300, cy=177, radius=135):
    return f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="url(#plate)" filter="url(#shadow)"/><circle cx="{cx}" cy="{cy}" r="{radius-13}" fill="none" stroke="#dbdbc8" stroke-width="2"/><circle cx="{cx}" cy="{cy}" r="{radius-29}" fill="#f6f4e6"/>'

def leaf(x,y,r=0,s=1,color='#6e8d45'):
    return f'<g transform="translate({x} {y}) rotate({r}) scale({s})"><path d="M0 0C-37-33-20-71 0-74 31-54 37-25 0 0Z" fill="{color}"/><path d="M0-5V-64M0-24l-12-12m12-2 13-14" fill="none" stroke="#d0d99e" stroke-width="1.3" opacity=".6"/></g>'

def tomato(x,y,r=18):
    return f'<g transform="translate({x} {y})"><circle r="{r}" fill="#d46b49"/><circle r="{r-4}" fill="#e38a5b"/><path d="M0 0 0-{r-5}M0 0l{r-5} 8M0 0l-{r-5} 8" stroke="#eebc82" stroke-width="2"/><circle cx="-5" cy="-5" r="2" fill="#f3d4a2"/><circle cx="6" cy="-4" r="2" fill="#f3d4a2"/><circle cy="7" r="2" fill="#f3d4a2"/></g>'

def salad():
    body=plate()
    for n in range(20):
        angle=n*2.399; radius=22+((n*31)%68)
        x=300+math.cos(angle)*radius; y=200+math.sin(angle)*radius*.75
        body+=leaf(round(x,1),round(y,1),n*63,.58,['#667e43','#8b9f60','#78954d','#acc17b'][n%4])
    for x,y in [(245,140),(325,214),(356,150),(255,223),(310,120)]:body+=tomato(x,y,17)
    for x,y in [(275,171),(330,162),(290,232),(365,195)]:
        body+=f'<circle cx="{x}" cy="{y}" r="19" fill="#658449"/><circle cx="{x}" cy="{y}" r="15" fill="#b7cfa0"/><circle cx="{x}" cy="{y}" r="8" fill="#dfdfb4"/>'
    for x,y in [(273,130),(310,185),(342,238),(224,187),(358,167),(287,207)]:body+=f'<rect x="{x}" y="{y}" width="17" height="14" rx="3" fill="#fff5d9" transform="rotate(18 {x} {y})"/>'
    return body

def pasta():
    body=plate()
    for n in range(38):
        a=n*2.399; r=(n*29)%87;x=300+math.cos(a)*r;y=174+math.sin(a)*r*.85
        body+=f'<path d="M{x-11:.1f} {y+8:.1f}q-15-12 0-23 22-10 23 6-2 12-17 7" fill="none" stroke="{["#e5ba62","#d7a353","#efca7e"][n%3]}" stroke-width="8" stroke-linecap="round" transform="rotate({n*47} {x} {y})"/>'
    for x,y,rot in [(250,160,100),(330,205,60),(352,150,140),(285,128,-50)]:body+=leaf(x,y,rot,.45)
    for x,y in [(256,218),(324,128),(354,200)]:body+=tomato(x,y,12)
    for x,y in [(280,161),(310,210),(345,175),(270,220),(307,126)]:body+=f'<path d="m{x} {y} 14-4-2 8Z" fill="#fff2ca"/>'
    return body

def bowl():
    body=plate()
    body+='<circle cx="300" cy="177" r="101" fill="#e7d1a1"/>'
    for n in range(90):
        a=n*2.399;r=(n*37)%93;x=300+math.cos(a)*r;y=177+math.sin(a)*r
        body+=f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="5" ry="2" fill="#f9e9c3" transform="rotate({n*31} {x} {y})"/>'
    for x,y in [(245,158),(264,132),(280,150),(245,195),(272,183)]:body+=f'<rect x="{x}" y="{y}" width="28" height="22" rx="8" fill="#d59a55" transform="rotate(-25 {x} {y})"/><path d="m{x+6} {y+6} 14 5m-14 3 12 5" stroke="#b77d43" stroke-width="2"/>'
    for x,y,rot in [(330,165,0),(360,193,60),(330,212,110),(345,140,40)]:body+=leaf(x,y,rot,.65)
    for x,y in [(305,226),(320,244),(340,224),(294,250)]:body+=f'<circle cx="{x}" cy="{y}" r="11" fill="#de9b53"/><circle cx="{x}" cy="{y}" r="6" fill="#edbc76"/>'
    return body

def toast():
    body=plate()
    for dx,rot in [(-45,-17),(48,14)]:
        body+=f'<g transform="translate({300+dx} 175) rotate({rot})"><path d="M-47-50Q-60-85-26-86H26Q60-85 47-50V65H-47Z" fill="#b98248"/><path d="M-39-46Q-52-76-24-77H24Q52-76 39-46V57H-39Z" fill="#dcb176"/>'
        for yy in range(-45,40,14):body+=f'<path d="M-29 {yy}q29-25 58 0" fill="none" stroke="#9ab46a" stroke-width="12" stroke-linecap="round"/>'
        body+='<path d="M-34-14Q-49 15-25 37 0 53 29 28 50 8 27-19 8-42-12-24-24-33-34-14" fill="#fff9e5"/><circle cx="2" cy="8" r="20" fill="#e5ac46"/><circle cx="-4" cy="2" r="7" fill="#edc26b" opacity=".6"/></g>'
    return body

def soup():
    body=plate()
    body+='<circle cx="300" cy="177" r="100" fill="#cf8c4b"/><circle cx="300" cy="177" r="92" fill="#dfa666"/><path d="M262 127c65-30 96 35 24 44-51 7-34 55 25 43 61-13 46-58-2-49" fill="none" stroke="#eed5ac" stroke-width="5" stroke-linecap="round"/>'
    for x,y,rot in [(285,185,20),(315,187,100),(301,168,-25)]:body+=leaf(x,y,rot,.35)
    for x,y in [(249,151),(347,216),(347,145),(268,227)]:body+=f'<rect x="{x}" y="{y}" width="14" height="13" rx="3" fill="#c48a50" stroke="#e4bf86" stroke-width="2" transform="rotate(25 {x} {y})"/>'
    return body

def eggs():
    body='<rect x="396" y="160" width="150" height="28" rx="12" fill="#475546" transform="rotate(-22 396 160)"/><circle cx="294" cy="178" r="139" fill="#485344" filter="url(#shadow)"/><circle cx="294" cy="178" r="128" fill="#2e4034"/><circle cx="294" cy="178" r="115" fill="#bc6242"/>'
    for n in range(20):
        a=n*2.399;r=(n*31)%95;x=294+math.cos(a)*r;y=178+math.sin(a)*r
        body+=f'<rect x="{x}" y="{y}" width="15" height="10" rx="3" fill="#d6824d" transform="rotate({n*19} {x} {y})"/>'
    for x,y in [(255,140),(335,185),(260,226)]:
        body+=f'<g transform="translate({x} {y})"><path d="M-30-20Q-47 0-29 24 0 40 27 20 44 2 25-22 0-37-13-21-25-30-30-20Z" fill="#f8edcd"/><circle r="18" fill="#e3ae45"/><circle cx="-4" cy="-5" r="6" fill="#eccb7c"/></g>'
    for x,y,rot in [(300,123,60),(343,233,-10),(230,184,20)]:body+=leaf(x,y,rot,.33)
    return body

for name,fn,bg in [('salad',salad,'#e1e7d6'),('pasta',pasta,'#eee5d4'),('bowl',bowl,'#e4e9d9'),('toast',toast,'#efe3cc'),('soup',soup,'#e5e8d7'),('eggs',eggs,'#e9ddcb')]:
    # Light woven napkin and tiny organic details lend depth without remote imagery.
    decor='<path d="M70-10h95l-35 380H35Z" fill="#ffffff24"/><path d="M90-10 55 370M125-10 90 370" stroke="#ffffff42" stroke-width="2"/>'
    (OUT/f'{name}.svg').write_text(svg(decor+fn()),encoding='utf-8')

hero='<ellipse cx="310" cy="302" rx="175" ry="18" fill="#33482d" opacity=".07"/>'+plate(310,183,137)
for x,y,rot,s in [(268,168,-65,.8),(351,147,60,.9),(323,205,150,.8),(275,229,-120,.7),(328,123,0,.65),(374,209,100,.6)]:hero+=leaf(x,y,rot,s)
for x,y,r in [(265,175,25),(339,211,22),(325,131,18),(292,227,17)]:hero+=tomato(x,y,r)
for x,y in [(294,146),(346,169),(285,206),(363,213)]:hero+=f'<rect x="{x}" y="{y}" width="22" height="17" rx="3" fill="#fff5d9" transform="rotate(20 {x} {y})"/>'
hero+='<g transform="translate(123 244) rotate(-22)"><path d="M0-75Q-45-53-31-6L0 58 32-6Q45-53 0-75Z" fill="#6e8c48"/><path d="M0-62V45" stroke="#b7ca83" stroke-width="3"/><path d="m-2-25-18-14m22 25 18-14m-22 27-17-13" stroke="#a0b674" stroke-width="2"/></g><g transform="translate(449 271)"><circle r="37" fill="#e0ae57"/><circle r="30" fill="#f0d491"/><circle r="25" fill="#edc779"/><path d="M0-25v50m-25-25h50m-43-18 36 36m-36 0 36-36" stroke="#f9e9b8" stroke-width="2"/></g>'
hero+=leaf(453,137,50,.65)+leaf(475,174,110,.55)+tomato(181,103,23)
hero+='<g fill="#768359"><circle cx="180" cy="290" r="3"/><circle cx="197" cy="296" r="2"/><circle cx="471" cy="93" r="3"/><circle cx="483" cy="105" r="2"/></g>'
(OUT/'hero.svg').write_text(svg(hero,'#eaf0df'),encoding='utf-8')
print(f'Created 7 original SVG illustrations in {OUT}')
