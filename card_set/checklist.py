cl = """1 Ty Cobb - Detroit Tigers
2 Walter Johnson - Washington Senators
3 Christy Mathewson - New York Giants
4 Honus Wagner - Pittsburgh Pirates
5 Nap Lajoie - Cleveland Naps
6 Tris Speaker - Cleveland Indians
7 Cy Young - Boston Red Sox
8 Grover Alexander - Philadelphia Phillies
9 Alexander Cartwright - NY Knickerbockers
10 Eddie Collins - Chicago White Sox
11 Lou Gehrig - New York Yankees
12 Willie Keeler - New York Highlanders
13 George Sisler - St. Louis Browns
14 Rogers Hornsby - St. Louis Cardinals
15 Frank Chance - Chicago Cubs
16 Johnny Evers - Chicago Cubs
17 Frankie Frisch - St. Louis Cardinals
18 Lefty Grove - Philadelphia Athletics
19 Carl Hubbell - New York Giants
20 Herb Pennock - New York Yankees
21 Pie Traynor - Pittsburgh Pirates
22 Mordecai Brown - Chicago Cubs
23 Jimmie Foxx - Philadelphia Athletics
24 Mel Ott - New York Giants
25 Dizzy Dean - St. Louis Cardinals
26 Rabbit Maranville - Boston Braves
27 Bill Terry - New York Giants
28 Joe DiMaggio - New York Yankees
29 Zack Wheat - Brooklyn Dodgers
30 Bob Feller - Cleveland Indians
31 Jackie Robinson - Brooklyn Dodgers
32 Edd Roush - Cincinnati Reds
33 Burleigh Grimes - Brooklyn Robins
34 Miller Huggins - New York Yankees
35 Casey Stengel - New York Yankees
36 Roy Campanella - Brooklyn Dodgers
37 Stan Musial - St. Louis Cardinals
38 Dave Bancroft - Philadelphia Phillies
39 Rube Marquard - New York Giants
40 Satchel Paige - Kansas City Monarchs
41 Yogi Berra - New York Yankees
42 Josh Gibson - Homestead Grays
43 Early Wynn - Cleveland Indians
44 Roberto Clemente - Pittsburgh Pirates
45 Warren Spahn - Milwaukee Braves
46 Jim Bottomley - St. Louis Cardinals
47 Whitey Ford - New York Yankees
48 Ernie Banks - Chicago Cubs
49 Eddie Mathews - Milwaukee Braves
50 Hack Wilson - Chicago Cubs
51 Al Kaline - Detroit Tigers
52 Duke Snider - Brooklyn Dodgers
53 Bob Gibson - St. Louis Cardinals
54 Frank Robinson - Cincinnati Reds
55 Juan Marichal - San Francisco Giants
56 Brooks Robinson - Baltimore Orioles
57 Don Drysdale - Los Angeles Dodgers
58 Rick Ferrell - St. Louis Browns
59 Harmon Killebrew - Minnesota Twins
60 Pee Wee Reese - Brooklyn Dodgers
61 Enos Slaughter - St. Louis Cardinals
62 Arky Vaughan - Pittsburgh Pirates
63 Willie McCovey - San Francisco Giants
64 Catfish Hunter - Oakland A's
65 Johnny Bench - Cincinnati Reds
66 Carl Yastrzemski - Boston Red Sox
67 Joe Morgan - Cincinnati Reds
68 Jim Palmer - Baltimore Orioles
69 Rod Carew - Minnesota Twins
70 Tony Lazzeri - New York Yankees
71 Hal Newhouser - Detroit Tigers
72 Tom Seaver - New York Mets
73 Reggie Jackson - Oakland A's
74 Steve Carlton - Philadelphia Phillies
75 Leo Durocher - Brooklyn Dodgers
76 Phil Rizzuto - New York Yankees
77 Richie Ashburn - Philadelphia Phillies
78 Mike Schmidt - Philadelphia Phillies
79 Larry Doby - Cleveland Indians
80 George Brett - Kansas City Royals
81 Orlando Cepeda - San Francisco Giants
82 Nolan Ryan - California Angels
83 Robin Yount - Milwaukee Brewers
84 Carlton Fisk - Chicago White Sox
85 Ozzie Smith - St. Louis Cardinals
86 Eddie Murray - Baltimore Orioles
87 Paul Molitor - Milwaukee Brewers
88 Wade Boggs - Boston Red Sox
89 Ryne Sandberg - Chicago Cubs
90 Tony Gwynn - San Diego Padres
91 Cal Ripken Jr. - Baltimore Orioles
92 Rickey Henderson - Oakland A's
93 Jim Rice - Boston Red Sox
94 Andre Dawson - Montreal Expos
95 Roberto Alomar - Toronto Blue Jays
96 Bert Blyleven - Minnesota Twins
97 Barry Larkin - Cincinnati Reds
98 Tom Glavine - Atlanta Braves
99 Greg Maddux - Atlanta Braves
100 Frank Thomas - Chicago White Sox"""

from card_set.models import Box, Pull, Video, Product, Set, Subset, Subject, Card

def do_checklist():
    subset = Subset.objects.get(pk=4)
    for line in cl.split("\n"):
        num_name, other = line.split(' - ')
        num = num_name.split(' ')[0]
        name_list = num_name.split(' ')[1:]
        name = " ".join(name_list)
        subject = Subject.objects.get(name=name)

        print(subject, num)

        c, _ = Card.objects.get_or_create(
            subject=subject, subset=subset
        )
        c.card_number = num
        c.save()
