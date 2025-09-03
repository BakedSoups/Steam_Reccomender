# Steam Recommender 
Find your new favorite game through game simularity, this algorithm attepts to reward video games that can't afford advertising

## Why does the Results page only have a steam review filter?
Ideally this is a oneshot app that gives you exactly what you were looking for first try!
if it isn't then we have done something wrong 
this app is in https://nextsteamgame.com/ 
## How this works
Steam Reccomender creates tags from 3 endpoints, 1 website and video reviews and apply weights to each tag
from this we also add a "unique" tag, this is what seperates this game from its others in its genre
then I upload it all into a sqlite database so when the user is searching for something its quick


## Comparisons
Using estimations from the ratios we form from the tags we compare the game the user input to other games in the database
applying:
 80% descriptive tags 
 20% unique in its genre tag

## Plans:
Currently only has around 350 games in the database, looking into scraping more ingo
going to implement chroma db and use vector simularitys as another "layer" to the simularity search
Ideally this fixes semantic differences

### Limitations
because the data pipeline is based of endpoints creating the db takes 3 days due to rate limiting because of this the data
will typically be 3 months old

### TLDR
Basically, we gather as much info on a game that we can, create tags, apply weights to the tags, and using that the user can find new games.
### Preview of the website 
![image](https://github.com/user-attachments/assets/3d99ff7f-d75b-48f4-a5c9-cf9a1c59a0fc)

![image](https://github.com/user-attachments/assets/5f2c0604-38f6-497f-ab21-1363ce99a627)


### Our glorious tech stack
![image](https://github.com/user-attachments/assets/2266a005-ea0d-4081-9836-69bc965eac51)

## Todo
- we should be able to have context of previous games if the review is mentioning it and build tags from that 
- Convert the MVP flask ap to fast api (starting to get limited)
- Implement Chroma db 
- humble bundle affiliates

## IMPORTANT Notice
if any of the reviewing companies I pulled data from would like to be removed from this program let me know
this is a silly data science project

I do have ads cause Im a broke college student, I just want to make it break even for internet traffic

