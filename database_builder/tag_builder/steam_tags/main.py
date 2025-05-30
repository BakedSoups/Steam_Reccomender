import sapi as sp

appid_list = [730, 440]
reviews = sp.get_reviews(appid_list[0], 4)
sp.print_reviews(reviews, 4)

print(reviews)