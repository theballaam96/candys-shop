from append_json import handlePR
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    pr_number_list = os.getenv("PR_NUMBER_LIST")
    lst = [int(x.strip()) for x in pr_number_list.split(",")]
    for x in lst:
        handlePR(x, False)