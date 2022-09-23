from sys import stdout
import json
import tweepy
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from itertools import chain, islice
from collections import Counter
# Keys
apiKey = "BfW33Mfnq6ryQM8LIDZ0GA4L7"
apiSecret = "VNWTwUGDYOgivFmD67JHELsYENrLbEvESMzGfmwn0jNP4ioDwZ"
accessToken = "702723328113451009-g9OskTZbnyrcJSrssi4lEf7F5MPUtbg"
accessSecret = "Zix4QTDXGaOh7MXDmzx95hIGYTiwtvs8MnF8BXU6cozpo"
bearerToken = "AAAAAAAAAAAAAAAAAAAAANg0hAEAAAAA5i7VMqv6s9hzIwA%2BnjG8RksACiw%3D4YzsH1pWn4yIsYb3STIBUXaJR4QYJJBGgkhridotzX3Og2yhkF"

#Global Variables
	#Initialize client (OAUTH 2.0 Bearer Token)
client = tweepy.Client(bearerToken, wait_on_rate_limit=True)
	#Declare dataframes
proData = pd.DataFrame()
antiData = pd.DataFrame()
proGraphData = pd.DataFrame()
antiGraphData = pd.DataFrame()
	#Keywords lists
proKeys = [	"VaxPlus",
			"VaccineMandate",
			"MandatoryVaccination",
			"VaccinesWork",
			"FullyVaccinated",
			"TrustTheScience",
			"VaccinesSaveLives",
			"VaccinatedForCovid",
			"AntivacinIdiots",
			"ProScience",
			"Antivaxxers",
			"CovidIsNotOver",
			"GetYourBooster"]
antiKeys = ["NoVaxMandates",
			"FuckTheVax",
			"FuckVaccines",
			"AntiVaccine",
			"NoForcedVaccines",
			"Notomandatoryvaccines",
			"NoVaccineMandates",
			"NoVaccineForMe",
			"SayNoToVaccines",
			"CovidVaccineIsPoison",
			"VaccinesArePoison",
			"VaccineDamage",
			"VaccineFailure",
			"VaccineHarm",
			"VaccineInjury",
			"VaccinesAreNotTheAnswer",
			"VaccinesKill",
			"NoVaccinePassports",
			"AntivaxxChronicles",
			"StopVaccination",
			"VaccineSideEffects",
			"NoBooster",
			"NoVaccine_NoPandemic",
			"DoNotComply"]
	#Tweet Search Queries		
proQuery = "GetVaccinated"
antiQuery = "NoVaccine"
for key in proKeys:
	proQuery = f"{proQuery} OR {key}"
for key in antiKeys:
	antiQuery = f"{antiQuery} OR {key}"
proQuery = f"({proQuery})"
antiQuery = f"({antiQuery})"

#Functions
	#Load data files
def init():
	global proData
	global antiData
	global antiGraphData
	global proGraphData
	vars = [proData, proGraphData, antiData, antiGraphData]
	files = ["./proDf.pkl", "./proGraph.pkl", "./antiDf.pkl", "./antiGraph.pkl"]
	for i in range(len(vars)):
		try:
			vars[i] = pd.read_pickle(files[i])
		except Exception:
			print(Exception)
	proData=vars[0]
	proGraphData=vars[1]
	antiData=vars[2]
	antiGraphData=vars[3]

	#Save data files
def save():
	global proData
	global antiData
	global proGraphData
	global antiGraphData
	vars = [proData, proGraphData, antiData, antiGraphData]
	files = ["./proDf.json", "./proGraph.json", "./antiDf.json", "./antiGraph.json"]
	for i in range(len(vars)):
		try:
			with open(files[i], 'w') as file:
				vars[i].to_json(file)
		except Exception as e:
			print(type(e))
			print(e.args)
			print(e)

	#Applied to dataframes to add liked_by column (users who liked the tweet)
def get_liked_by(id: str) -> list:
	res = client.get_liking_users(id, max_results=100)
	if res.data is None:
		return []
	liked_by = [user.id for user in res.data]
	return liked_by

	#Applied to dataframes to add follower column
def get_followers(id: str) -> list:
	res = client.get_users_followers(id, max_results=999)
	if res.data is None:
		return []
	followers = [user.id for user in res.data]
	return followers

	#Applied to dataframes to add following column
def get_following(id: str) -> list:
	res = client.get_users_following(id, max_results=999)
	if res.data is None:
		return []
	following = [user.id for user in res.data]
	return following

	#Applied to dataframes to add edges column
def create_edges(row: pd.Series) -> list:
	edges = []
	for id in row['followers']:
		edges.append((id, row['user']))
	for id in row['following']:
		edges.append((row['user'], id))
	return edges

	#Collects tweet search response and returns a dataframe
def get_tweets(query: str) -> pd.DataFrame:
	countRes = client.get_recent_tweets_count(query)
	loops = int(countRes.meta['total_tweet_count']/100)
	if loops > 450:
		loops = 450
	
	until = None
	tweets = []
		#Gets all tweets up to 7 days old
	for i in range(100):
		#Get API search response for hashtags
		res = client.search_recent_tweets(query, max_results=100, expansions="author_id", tweet_fields="public_metrics", until_id=until)
		tweets = tweets + res.data
		until = tweets[len(tweets)-1].id
		stdout.write(f"\rSearch Progress: {i+1}/{100}")
		stdout.flush()
	print("\n")
	userId = [tweet.author_id for tweet in tweets]
	tweetId = [tweet.id for tweet in tweets]
	likes = [tweet.public_metrics['like_count'] for tweet in tweets]
		#Initialize dataframes
	df = pd.DataFrame(data={'user':userId, 'tweet':tweetId, 'likes':likes})
		#Sort dataframes by likes
	df.sort_values(by=['likes'], ascending=False, inplace=True, ignore_index=True)
		#Only return the top 75 most liked tweets
	df.drop(list(range(75,len(df.index))), inplace=True)
	return df

	#Finds count of duplicate users in liked_by column and returns top 15
def find_mutuals(df: pd.DataFrame) -> list:
	mutualCount = Counter(chain.from_iterable(df['liked_by']))
	sortedCount = {k: v for k, v in (sorted(mutualCount.items(), key=lambda item: item[1], reverse=True)[0:15])}
	print("Mutual Likes:")
	print(sortedCount)
	return list(sortedCount.keys())

	#Creates friendship network from dataframe
def create_graph(df: pd.DataFrame) -> nx.DiGraph:
	graph = nx.DiGraph()
	for edges in df['edges']:
		graph.add_edges_from(edges)
	return graph
	
	#Removes nodes with degree of 1
def clean_graph(graph: nx.DiGraph, i: int = 1) -> None:
	size = 300
	while True:
		removed = [node for node in graph.nodes() if graph.degree(node) <= i]
		if removed == [] or graph.number_of_nodes() == size:
				break	
		for node in removed:
			if graph.number_of_nodes() == size:
				break
			graph.remove_node(node)
			
	if(graph.number_of_nodes()>size):
		i += 1
		clean_graph(graph, i)

	#Takes a query and returns tweet dataframe and graph dataframe
def gen_tweet_data(query: str) -> tuple:
	df = get_tweets(query)
	print("Getting tweet likes...")
	df['liked_by'] = df['tweet'].apply(get_liked_by)
	mut = find_mutuals(df)
	graphDf = pd.DataFrame(data={'user':mut})
	print("Getting Follows...")
	graphDf['followers'] = graphDf['user'].apply(get_followers)
	graphDf['following'] = graphDf['user'].apply(get_following)
	graphDf['edges'] = graphDf.apply(create_edges, axis=1)
	return (df, graphDf)

def draw_histogram(graph: nx.DiGraph, color: str, title: str):
	degSorted = sorted([deg for node, deg in graph.degree()], reverse=True)
	degCount = Counter(degSorted)
	deg, cnt = zip(*degCount.items())
	fig, ax = plt.subplots()
	plt.bar(deg, cnt, width=.8, color=color)
	plt.title(title)
	plt.ylabel("Count")
	plt.xlabel("Degree")
	ax.set_xticks([d + .4 for d in deg])
	ax.set_xticklabels(deg)
	plt.show()

def present():
	proGraph = create_graph(proGraphData)
	antiGraph = create_graph(antiGraphData)
	clean_graph(proGraph)
	clean_graph(antiGraph)

	nx.draw(proGraph)
	plt.show()
	draw_histogram(proGraph, 'b', "ProVaccine Degree Histogram")

	nx.draw(antiGraph)
	plt.show()
	draw_histogram(antiGraph, 'r', "AntiVaccine Degree Histogram")

#Main Code
init()
proGraph = create_graph(proGraphData)
antiGraph = create_graph(antiGraphData)

clean_graph(proGraph)

clustering = nx.clustering(proGraph)
clustSort = sorted([deg for node, deg in clustering.items()], reverse=True)
print(clustSort)