import smtplib
import ssl

from playwright.sync_api import sync_playwright,TimeoutError
from ollama import chat
import os
import sqlite3

from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv()


class Browser:

    def open_website(self):

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            slow_mo=2000
        )

        self.page = self.browser.new_page()

        self.page.goto(
            "https://finance.yahoo.com/markets/",
            wait_until="domcontentloaded"
        )

        return self.page

    def close_website(self):
        self.browser.close()
        self.playwright.stop()






class StockDataScraper:

    def __init__(self, browser):
        self.browser = browser
        self.page = browser.open_website()
        self.user_input = input("enter stock symbol:")


    def get_stock_data(self):
      try:

        search_input = self.page.get_by_label("Quote Lookup")
        search_input.fill(self.user_input)

        first_option = self.page.get_by_role("option").first
        first_option.click()

      except TimeoutError:

        print("Stock not found")


      self.page.wait_for_selector("li.nav-item")

      historical_data = self.page.get_by_text("Historical Data")
      historical_data.click()

      historical_data.click()

      headers = self.page.locator(
            "table thead tr th"
        ).all_inner_texts()

      rows = []

      first_row = self.page.locator(
            "tbody tr"
        ).nth(0)

      row_values = first_row.locator(
            "td"
        ).all_inner_texts()

      for row in range(0, len(row_values), 7):

            current_row = row_values[row:row + 7]



            rows.append(current_row)

      return headers, rows
    








        

        


 



class DataBase:

   def __init__(self,rows_value):
       # creat SQL file
       _,rows = rows_value.get_stock_data()
       self.rows_value= rows[0]



       self.connection = sqlite3.connect("FinanceData.db")

       self.cursor = self.connection.cursor()
       self.cursor.execute("""
              CREATE TABLE IF NOT EXISTS stocks(
                  date TEXT PRIMARY KEY,
                  open REAL,
                  high REAL,
                  low REAL,
                  close REAL,
                  adj_close REAL,
                  volume INTEGER
              )
              """)

   def save_stock_data(self):


     self.cursor.execute("""insert or ignore into stocks values (?,?,?,?,?,?,?)""",self.rows_value)
     self.connection.commit()

     return self.cursor.rowcount







   def get_last_20_days(self):
       self.cursor.execute("select * from stocks order by rowid desc limit 20;")

       return self.cursor.fetchall()


   def get_last_day(self):
       self.cursor.execute("select * from stocks order by rowid desc limit 1;")

       return self.cursor.fetchone()



   def get_total_records(self):
       self.cursor.execute("select count(*) from stocks")

       return self.cursor.fetchone()[0]

   def close_database(self):

       self.connection.close()









class StockAnalyzer:

    def __init__(self,data_base_value):
        self.data_base_value = data_base_value



    def load_data(self):

           total_records = self.data_base_value.get_total_records()



           if total_records >= 20:

                return self.data_base_value.get_last_20_days()

           else:

               return self.data_base_value.get_last_day()


class AiAnalyzer:



    def __init__(self,analyze_data):

        self.analyze_data = analyze_data



        self.prompt = 0

    def generate_analysis(self):



        if self.analyze_data.data_base_value.get_total_records()>= 20:

            self.prompt = """

You are a financial market analyst.

Analyze the last 20 trading days.

Provide:

- Overall trend.

- Price behavior during the period.

- Important observations.

- Short-term outlook.

Write in English only.

Rating:

Bullish, Bearish, or Neutral.

"""

        else:

            self.prompt = """

You are a financial market analyst.

Write in English only.

Do not use:

- Arabic.

- Chinese.

- Japanese.

- Russian.

- Emojis.

- Special decorative symbols.

Based only on today's stock data, provide:

- A summary of today's performance.

- An explanation of the price movement.

If the data is insufficient for an accurate prediction, mention only the most likely direction.

The response must follow this format exactly:

Today's Summary:

- ...

- ...

- ...

Price Analysis:

- ...

- ...

Rating:

Bullish, Bearish, or Neutral

Do not repeat any sentence.

Do not repeat any section.

Do not write anything outside this format.

"""

        ai_response = chat(
            model="Qwen3:14b",
            messages=[
                {
                    "role": "system",
                    "content": self.prompt
                },
                {
                    "role": "user",
                    "content": f"""
Stock Data:

{self.analyze_data.load_data()}

Analyze today's stock performance using only this data.
"""
                }
            ]
        )

        ai_response=ai_response.message.content
        return ai_response


class Email :

    def __init__(self,message):
        self.message = message

    def send_email(self):
        email_message = EmailMessage()
        user_email =os.getenv("USER_EMAIL","")

        user_pass = os.getenv("USER_PASSWORD","")
        receiver=os.getenv("RECEIVER_EMAIL","")

        email_message["from"] = user_email
        email_message["to"] = receiver
        email_message["subject"] = "Daily Stock Report"

        email_message.set_content(self.message)

        host = "smtp.gmail.com"
        port = 465

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user=user_email, password=user_pass)
            server.send_message(email_message)



if __name__ == "__main__":


    browser = Browser()

    stock_scraper = StockDataScraper(browser)



    dataBase_storage = DataBase(stock_scraper)


    saved=dataBase_storage.save_stock_data()

    if saved:



        browser.close_website()

        stock_analyzer = StockAnalyzer(dataBase_storage)

        ai_analyzer = AiAnalyzer(stock_analyzer)

        message=ai_analyzer.generate_analysis()

    else:
        message="No new trading data available today."

    email = Email(message)
    email.send_email()

    dataBase_storage.close_database()

