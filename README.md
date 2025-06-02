# Steam Recommender 
Find your new favorite game through game simularity, this algorithm attepts to reward video games that can't afford advertising

this app is in https://nextsteamgame.com/ 
## High-Level on how this works 
sorting steam games by the default steam tags and by what is most relevant is functional but from my personal expeirence it can be limited, looking for a desired game because I like the nuances is hard to do if its official steam tags are just "JRPG" and "Action" 
to solve this I procedurally create new game tags from reviews to help form vectors on what a games focus is, then place it in a Genre heiarchy tree,

## How this works
I gather review data from 3 endpoints, 1 website and youtube video reviews, then I filter our the reviews and sort them by what is the most descriptive.From that using the default steam tags I procedurally determine where this game lands in the genre umbrella (Main Genre -> Sub genre -> sub sub genre) 

### For example: 
Persona 5 
Input: 
 Review:
 "this game has great cel shaded graphics, a social link system, a great balance of living a highschool life then exploring the dungeon, along with a jazz sound track" 
 Steam tags:

Output: 
Descriptive Tag Vector:30% JRPG 20% Social links 30% Action 20% Jazz
SUbjective Tag Vector :50% non-replayable 30% Artistic 20%
Genre: JRPG -> Turn-Based -> Social-link 
Art style : cel shaded 
Music : Jazz 

## Searching 
When the user inputs a game we go to the heirachy tree and go to the sub sub genre then do vector comparisons if there are vectors that are way of we move up the tree to sub genre, This system helps keep the results on theme but also makes sure to go for "game play" first
Additionally I add a 25% bonus if there is a game that shares the same Subjective tag
I also add a 10% boost if it has both Art style + Music

### Limitations
because the data pipeline is based of endpoints creating the db takes 3 days due to rate limiting because of this the data
will typically be 3 months old

### TLDR
Basically, we gather as much info on a game that we can, create tags, apply weights to the tags, and using that the user can find new games.
### Preview of the website 
![image](https://github.com/user-attachments/assets/91219a29-adab-4cfc-abee-3a462741dcaf)
![image](https://github.com/user-attachments/assets/722b1706-3bd8-48d8-8eb5-934d260a3fbd)

### Whats under the Hood
![image](https://github.com/user-attachments/assets/b1e3cb2b-4166-4313-b554-713aa32edf32)
![image](https://github.com/user-attachments/assets/10b85291-8a23-406b-922b-6cc93554452c)


### Our glorious tech stack
![image](https://github.com/user-attachments/assets/2266a005-ea0d-4081-9836-69bc965eac51)

## Todo
- Make the search landing page auto suggest beyound fuzzy
- add more depth to tag matching
- In the results page add buttons to sort by reviews and tags
- Add multiple game inputs
- Art style image classification based on game preview images

## IMPORTANT Notice
if any of the reviewing companies I pulled data from would like to be removed from this program let me know
this is a silly data science project

I do have ads cause Im a broke college student, I just want to make it break even for internet traffic

