import praw
import time
import os
from langchain.tools import tool
from crewai import Agent, Task, Process, Crew
from custom_functions import post_to_twitter_callback
from langchain.agents import load_tools
from langchain_openai import ChatOpenAI
import os
import time
from langchain.tools import tool
from dotenv import load_dotenv

#load environment vars
load_dotenv() 

# openai
api = os.environ.get("OPENAI_API_KEY")

#reddit
client_id_re= os.environ.get("REDDIT_CLIENT_ID") 
client_secret_re=os.environ.get("REDDIT_CLIENT_SECRET") 

client_id2_re = os.environ.get("REDDIT_CLIENT_ID2") 
client_secret2_re = os.environ.get("REDDIT_CLIENT_SECRET2") 



llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# To load Human in the loop
human_tools = load_tools(["human"])

class BrowserTool:
    @tool("Scrape reddit content")
    def scrape_reddit(max_comments_per_post=7):
        """Useful to scrape a reddit content"""
        reddit = praw.Reddit(
            client_id=client_id_re,
            client_secret=client_secret_re,
            user_agent="user-agent",
        )
        subreddit = reddit.subreddit("CryptoCurrency")
        scraped_data = []

        for post in subreddit.hot(limit=12):
            post_data = {"title": post.title, "url": post.url, "comments": []}

            try:
                post.comments.replace_more(limit=0)  # Load top-level comments only
                comments = post.comments.list()
                if max_comments_per_post is not None:
                    comments = comments[:7]

                for comment in comments:
                    post_data["comments"].append(comment.body)

                scraped_data.append(post_data)

            except praw.exceptions.APIException as e:
                print(f"API Exception: {e}")
                time.sleep(60)  # Sleep for 1 minute before retrying

        return scraped_data
    

"""
- define agents that are going to research latest cryptocurrency developments and write a report about it 
- explorer will use access to internet and CryptoCurrency subreddit to get all the latest news
- formatter will check the output of the explorer to match the desired format
"""

explorer = Agent(
    role="Senior Researcher",
    goal="Find and explore the most exciting developments on CryptoCurrency subreddit today",
    backstory="""You are and Expert strategist that knows how to spot emerging trends and important events in Crypto, blockchain and web3 TODAY. 
    You're great at finding exciting projects on CryptoCurrency subreddit. You turned scraped data into detailed reports with titles
    of the most exciting developments in the crypto world. ONLY use scraped data from CryptoCurrency subreddit for the report. Make sure not to forget the links to the posts.
    """,
    verbose=True,
    allow_delegation=False,
    tools=[BrowserTool().scrape_reddit] + human_tools,
   llm=llm,  
)

formatter = Agent(
    role="Expert Writing formatter",
    goal="Make sure the output is in the right format. Make sure that the tone and writing style is compelling, simple and concise",
    backstory="""You are an Expert at formatting text from technical writers. You can tell when a report text isn't concise,
    simple or engaging enough. You know how to make sure that text stays technical and insightful by using layman terms. You know how to format a report properly.
    """,
    verbose=True,
    allow_delegation=True,
    llm=llm,
)

task_report = Task(
    description="""Use and summarize scraped data from subreddit CryptoCurrency to make a detailed report on today's developments in crypto. Use ONLY 
    scraped data from CryptoCurrency to generate the report. Your final answer MUST be a full analysis report, text only, ignore any code or anything that 
    isn't text except for links. The report has to have bullet points and with 5-10 exciting crypto developments. 
    Each bullet point MUST contain 3 sentences that refer to one specific development you found on subreddit CryptoCurrency. Each bullet point must contain a link to the post.  
    """,
    agent=explorer,
    expected_output="""A detailed report with bullet points each containing 3 sentences about a specific crypto development found on the CryptoCurrency subreddit."""
)

task_formatter = Task(
    description="""
        Format the explorer's output for Twitter posting by structuring the information according to the following template:
        
        - For each news item, begin with the title.
        - Follow the title with a bullet point listing interesting facts about the news item.
        - Ensure each fact is compelling, engaging, and provides value to the reader.
        - Conclude each news item summary with a bullet point that includes a link to the original post.
        
        The output must be clearly structured, contain accurate and engaging information, and each news item must have a corresponding link. Your task is to verify the structure, assess the compelling nature of the text, and ensure all links are correctly included.
    """,
    agent=formatter,
    expected_output="""
        The formatted output should look like this for each news item:
        
        [Title of News Item]
        - An interesting and engaging fact about the news item. The fact should be compelling and present the news in an engaging way.
        - A direct link to the original post for readers to find more information.
        
        "Title of News Item" should be replaced with the actual title. This format should be repeated for each news item included in the explorer's output, ensuring a consistent and engaging reader experience.
    """,
)


# instantiate crew of agents
crew = Crew(
    agents=[explorer, formatter],
    tasks=[task_report, task_formatter],
    verbose=2,
    process=Process.sequential,  # Sequential process will have tasks executed one after the other and the outcome of the previous one is passed as extra content into this next.
)

# Get your crew to work!
result = crew.kickoff()
post_to_twitter_callback(result)
print("######################")
print(result)