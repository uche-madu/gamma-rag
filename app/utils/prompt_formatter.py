from langchain_core.prompts import ChatPromptTemplate

prompt_template = ChatPromptTemplate.from_messages([
    ("system", 
        "You are an experienced financial analyst specializing in investment research."
        " Your task is to analyze relevant stock market insights based on retrieved data."
        " Ensure your response is data-driven, structured, and easy to understand."
    ),
    ("human", 
        "A user is inquiring about {company_name} ({stock_symbol}).\n"
        "They are particularly interested in {topics_of_interest} within the date range {date_range}.\n"
        "The user's sentiment toward this investment is {user_sentiment}.\n"
        "Today's date is {current_date}.\n\n"
        "### Relevant Facts from Past Interactions:\n"
        "{previous_facts}\n\n"
        "### Retrieved Financial Articles:\n"
        "{formatted_articles}\n\n"
        "Based on the above, analyze the company's current market position and provide an investment assessment.\n"
        "### Response Format:\n"
        "1. **Summary of Key Financial Insights:**\n"
        "2. **Advantages of Investing:**\n"
        "3. **Risks and Disadvantages:**\n"
        "4. **Sentiment-Based Recommendation:**\n\n"
        "Ensure your response is professional, structured, and actionable."
    ),
])
