# Steam Recommender
Find your new favorite game only through game similarity, this algorithm attempts to reward video games that can't afford advertising

## Why does the Results page only have a steam review filter?
Ideally this is a oneshot app that gives you exactly what you were looking for first try!
if it isn't then we have done something wrong
this app is in https://nextsteamgame.com/
## How this works
Steam Reccomender procedurally creates tags from 3 endpoints, 1 website and video reviews( sorted by credibility ) and apply weights to each tag
from this we also add a "unique" tag, this is what separates this game from its others in its genre
then I upload it all into a sqlite database so when the user is searching for something its quick


#### Comparisons
Create vectors from weighted tags (2 action, 3 story, 5 rpg)
uses vector simularity to find close matches
weighs if a game matches its "unique" tag in a genre

### Limitations
because the data pipeline is based of endpoints creating the db takes 3 days due to rate limiting because of this the data
will typically be 3 months old

### Preview of the website
![image](https://github.com/user-attachments/assets/3d99ff7f-d75b-48f4-a5c9-cf9a1c59a0fc)
![image](https://github.com/user-attachments/assets/5f2c0604-38f6-497f-ab21-1363ce99a627)
### the pipeline (this all automatically happens if you simply run ochestrator.go)
![image](https://github.com/user-attachments/assets/ae475912-1b9e-4f3d-a29f-35788156a07f)
![image](https://github.com/user-attachments/assets/de22a2ae-622b-45ab-8ea2-a14de4357bb1)
### Our glorious tech stack
![image](https://github.com/user-attachments/assets/287e19f2-49c8-4ba8-ba3c-fc06ca2ef8b1)

## Plans:
Rework Main genre tags
Make the procedurally generated tags searchable

## IMPORTANT Notice
if any of the reviewing companies I pulled data from would like to be removed from this program let me know
this is a silly data science project

I do have ads cause Im a broke college student, I just want to make it break even for internet traffic



