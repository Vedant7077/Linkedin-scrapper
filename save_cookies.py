import pickle
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://www.linkedin.com/login")

input("🔑 Login manually in the browser, then press Enter here...")

pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
print("✅ Cookies saved to cookies.pkl")

driver.quit()
