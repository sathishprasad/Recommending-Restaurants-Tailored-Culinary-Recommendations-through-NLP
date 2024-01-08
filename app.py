import streamlit as st
import pandas as pd
from PIL import Image
from streamlit_folium import st_folium
import folium
from bs4 import BeautifulSoup
import requests
from streamlit_image_select import image_select
import re
import numpy as np
import urllib.parse
from dateutil import parser
from sklearn.metrics.pairwise import cosine_similarity



st.cache_data()
def connect():
    df = pd.read_csv("app_demo_data_full.csv")
    features = np.load('word2vec_vectors.npy')
    df['image_url'] = df['image_url'].fillna("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/No-Image-Placeholder.svg/832px-No-Image-Placeholder.svg.png")



    return df,features

def format_business_hours(hours):
    # Insert a comma and space between the two time ranges
    # Look for the pattern 'PM' followed by a digit and insert ', '
    formatted_hours = re.sub(r'(PM)(\d)', r'\1, \2', hours)
    return formatted_hours

def restaurant_recommendation(name, data, indices,features):
    # Load the features
    features = features

    if indices[name].ndim > 0:
        index = indices[name][0]
    else:
        index = indices[name]

    # Compute similarity scores with other features
    vector_2d = features[index].reshape(1, -1)
    similarity_scores = cosine_similarity(vector_2d, features).flatten()

    # Create a list of (index, similarity score) pairs
    scores_with_index = list(enumerate(similarity_scores))

    # Sort the restaurants based on similarity scores
    sorted_scores = sorted(scores_with_index, key=lambda x: x[1], reverse=True)

    # Filter out scores that are less than or equal to 0.45
    filtered_scores = [score for score in sorted_scores if score[1] > 0.75]

    # Get top 10 similar restaurants (excluding the first which is the restaurant itself)
    top_restaurants = filtered_scores[1:11]


    restaurant_indices = [i[0] for i in top_restaurants]


    recommended_df = data.iloc[restaurant_indices].copy()
    recommended_df['Recommended'] = [round(i[1] * 100, 2) for i in top_restaurants]
    recommended_df['Recommended'] = recommended_df['Recommended'].apply(lambda x: f'{x}%')



    return recommended_df

def clean_and_split_review(data_list):
    business_hours = []
    faqs = []
    yelp_info = []
    other_info = []

    for item in data_list:
        # Check for business hours pattern
        if re.match(r'\d{1,2}:\d{2} [APM]{2} - \d{1,2}:\d{2} [APM]{2}', item):
            business_hours.append(item)
        # Check for FAQ pattern
        elif re.search(r'Q:', item) and re.search(r'A:', item):
            faqs.append(item)
        # Check for Yelp specific info
        elif 'Yelp' in item:
            yelp_info.append(item)
        # Other info
        else:
            other_info.append(item)

    return {
        'business_hours': business_hours,
        'faqs': faqs,
        'yelp_info': yelp_info,
        'other_info': other_info
    }

def clean_and_split_faq(text):
    # Remove unwanted characters
    cleaned_text = text.replace('\xa0', ' ')

    # Remove specific patterns like names, time references, and additional statements
    cleaned_text = re.sub(r'\b[A-Za-z]+ [A-Z]\.,?\sBusiness Owner\s\d+ years? ago', '', cleaned_text)
    cleaned_text = re.sub(r'\b[A-Za-z]+ [A-Z]\.,?\s\d+ years? ago', '', cleaned_text)
    cleaned_text = re.sub(r'\d+ people found this helpful', '', cleaned_text)
    cleaned_text = re.sub(r'See question details|See \d+ more answer(s)?', '', cleaned_text)
    cleaned_text = re.sub(r'more[A-Za-z ]+\.', '', cleaned_text)

    # Use regular expression to find all Q&A pairs
    pattern = r'Q:(.*?)A:(.*?)(?=Q:|$)'
    qa_pairs = re.findall(pattern, cleaned_text)

    # Process each pair to clean and separate questions and answers
    processed_qa_pairs = []
    for pair in qa_pairs:
        question = pair[0].strip()
        answer = pair[1].strip()
        # Additional cleaning for the answer to remove any trailing business owner and time references
        answer = re.sub(r'\s?[A-Za-z]+ [A-Z]\.,?\sBusiness Owner\s\d+ years? ago.*', '', answer)
        answer = re.sub(r'\s?[A-Za-z]+ [A-Z]\.,?\s\d+ years? ago.*', '', answer)
        processed_qa_pairs.append({'question': question, 'answer': answer})

    return processed_qa_pairs

def split_and_clean_food_ideas(text):
    # Split the text at each occurrence of 'Reviews'
    food_items = re.split(r'Reviews', text)

    # Further clean each food item
    cleaned_food_items = []
    for item in food_items:
        # Remove '\xa0', 'Photos', 'Photo' and any numbers
        clean_item = re.sub(r'(\d+ Photos|\d+ Photo|\xa0|\d+)', '', item).strip()
        if clean_item:  # Ensure the item is not empty
            clean_item = clean_item.replace('$','')
            clean_item = clean_item.replace('.','')
            clean_item = clean_item.replace('Price varies','')
            clean_item = clean_item.replace('Review','')
            cleaned_food_items.append(clean_item)

    return cleaned_food_items

def customer_reviews(response):
  #response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')

  # Find all <li> elements with the specified class
  li_elements = soup.find_all('ul', class_='list__09f24__ynIEd')

  span_texts = [span.get_text() for li in li_elements for span in li.find_all('span')]

  return span_texts

def scrape_restaurant_info(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    information_data = []
    review_data = []
    recommendation_data ={}
    website_links =[]


    response = requests.get(url)

    span_texts = customer_reviews(response)
    progress_ratings = rating_bars(response)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        review_elements = soup.find_all(class_='css-1p9ibgf')

        for element in review_elements:
            a_tag = element.find('a')
            if a_tag and a_tag.has_attr('href'):
                href = a_tag['href']

                parsed_url = urllib.parse.urlparse(href)
                query_string = urllib.parse.parse_qs(parsed_url.query)

                actual_url = query_string.get('url', [""])[0]
                if actual_url:
                    actual_url_parsed = urllib.parse.urlparse(actual_url)
                    website_links.append(actual_url_parsed.netloc)

        # Extract basic info
        ratings_basic_info = soup.find_all(class_='css-1fdy0l5')
        for basic_info in ratings_basic_info:
            information_data.append(basic_info.text)

        # Extract reviews
        reviews = soup.find_all(class_='list__09f24__ynIEd')
        for review in reviews:
            review_data.append(review.text)

        # Extract popular dishes
        popular_dishes = soup.find_all(class_='css-wtz7x')
        for dish in popular_dishes:
            recommendation_data['popular_dishes'] = dish.text

        # Extract popular dishes' images
        popular_dishes_images = soup.find_all('img', class_='dishImageV2__09f24__VT6Je')
        dish_urls = []
        for dish_image in popular_dishes_images:
            dish_url = dish_image.get('src')
            if dish_url:
                dish_urls.append(dish_url)
        recommendation_data['dish_images'] = dish_urls


        divs = soup.find_all('div', class_='arrange-unit__09f24__rqHTg arrange-unit-fill__09f24__CUubG css-1qn0b6x')
        amenities = [span.get_text() for div in divs for span in div.find_all('span')]


        #span_texts = customer_reviews(url)
        #progress_ratings = rating_bars(url)


    else:
        information_data['basic_info'] = ''
        recommendation_data['reviews'] = ''
        recommendation_data['popular_dishes'] = ''
        recommendation_data['dish_images'] = []
        amenities = []
        website_links = []
        span_texts = ''
        progress_ratings = ''



    return information_data,review_data,recommendation_data,amenities,website_links,span_texts,progress_ratings

def find_dates_and_reviews(data_list):
    dates_and_reviews = {}
    last_date = None

    for item in data_list:
        item = item.strip()
        if not item:
            continue  # Skip empty strings

        # Check if the item is a date
        try:
            parsed_date = parser.parse(item, fuzzy=False)
            # If we haven't already found a review for a previous date, store this date
            if last_date is None:
                last_date = parsed_date.strftime("%b %d, %Y")
        except ValueError:
            # If it's not a date and we have a recent date
            if last_date:
                # Check if the item's length is more than 10
                if len(item) > 17:
                    dates_and_reviews[last_date] = item
                    last_date = None  # Reset last_date after assigning a review

    return dates_and_reviews

# def amenities(url):
#     services = []
#     try:
#         options = Options()
#         #options.add_argument("--headless")
#         options = Options()
#         options.add_argument("--headless")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-features=NetworkService")
#         options.add_argument("--window-size=1920x1080")
#         options.add_argument("--disable-features=VizDisplayCompositor")
#
#
#
#         with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options) as driver:
#             driver.get(url)
#
#             # Use WebDriverWait to wait for the button to be clickable
#             try:
#                 button_xpath = '//*[@id="main-content"]/section[4]/div[2]/button'
#                 WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, button_xpath))).click()
#             except Exception as e:
#                 print(e)
#                 st.write(e)
#
#             # BeautifulSoup parsing
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             target_div = soup.find('div', class_='arrange__09f24__LDfbs gutter-2__09f24__CCmUo layout-wrap__09f24__GEBlv layout-2-units__09f24__PsGVW css-1qn0b6x')
#             if target_div:
#                 spans = target_div.find_all('span')
#                 st.write(spans)
#                 services = [span.get_text().strip() for span in spans if span.get_text().strip()]
#
#     except Exception as e:
#         print(e)
#         st.write(e)
#
#     return services
#
#     return service

def rating_bars(response):
        #response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        classes_to_check = [
            "css-du03s3",
            "css-1tdsrk2",
            "css-s2hdx2",
            "css-11a1mbi",
            "css-1wilm3t"
        ]

        all_widths = []

        for class_name in classes_to_check:
            elements_with_style = soup.find_all(class_=class_name)

            for element in elements_with_style:
                style = element.get('style')
                if style and 'width' in style:

                    width = style.split('width:')[-1].split(';')[0].strip()
                    width = width.replace('%', '')
                    width = float(width)

                    all_widths.append(width)

        return all_widths

def format_group(items):
    return ' '.join(f'<span style="display: inline-block; width: 25%;"><ul style="list-style-type:disc; margin: 0;"><li>{item}</li></ul></span>' for item in items)

def main():
    img = Image.open('logo2.png')

    st.title("TasteMatch: Discover Your Next Favorite Restaurant")
    #st.write("Discover new dining gems effortlessly with our app: just pick your favorite restaurant, and we'll match you with similar, top-rated spots near you. Expand your culinary world with confidence and ease!")
    #st.text("Explore Culinary Delights: Effortlessly Find Restaurants Tailored to Your Taste")
    st.write("Have you ever found yourself hesitant to try new restaurants, worried that they might not live up to your expectations, leaving you sticking to the same old places? Well, fear no more! That's precisely the reason I developed this innovative solution. Just tap on the menu bar, select your go-to restaurant from your current location, and voilà! You'll discover a curated list of similar restaurants, handpicked based on user reviews and preferences. This feature is designed to broaden your culinary horizons while staying within your comfort zone, ensuring you enjoy every dining experience. So, get ready to explore new flavors and dining spots with confidence!")
    #st.text("Have you ever found yourself hesitant to try new restaurants, worried that they might \nnot live up to your expectations, leaving you sticking to the same old places? Well, fear no more!\nThat's precisely the reason I developed this innovative solution. Just tap on the menu bar,\nselect your go-to restaurant from your current location, and voilà! You'll discover\na curated list of similar restaurants, handpicked based on user reviews and preferences.\nThis feature is designed to broaden your culinary horizons while staying within your comfort zone, ensuring you\nenjoy every dining experience. So, get ready to explore new flavors and dining spots with confidence!")
    data,similarity = connect()
    recommendation_data = data

    st.sidebar.image(img)

    state_list = data['State'].unique().tolist()
    state = st.sidebar.selectbox("Choose your State",state_list)
    data = data[data['State']==state]

    city_list = data['City'].unique().tolist()
    city = st.sidebar.selectbox("Choose your City",city_list)
    data = data[data['City']==city]

    restaurants_list = data['name'].unique().tolist()
    restaurant = st.sidebar.selectbox("Choose your favourite Restaurant",restaurants_list)
    reference_index = data.index[data['name'] == restaurant].tolist()[0]

    option = st.sidebar.toggle("Looking for a Restaurant in another state?")

    st.session_state['Option'] = 'No'
    if option:
        st.session_state['Option'] = 'Yes'
        t_state_list = state_list
        t_state_list.append("All")
        target_state = st.sidebar.multiselect("Choose your target State/States",t_state_list,default='All')
        if 'All' not in target_state:
            recommendation_data = recommendation_data[recommendation_data['State'].isin(target_state)]

        t_city_list = recommendation_data['City'].unique().tolist()
        t_city_list.append("All")
        target_city = st.sidebar.multiselect("Choose your target City/Cities",t_city_list ,default='All')
        if 'All' not in target_city:
            recommendation_data = recommendation_data[recommendation_data['City'].isin(target_city)]

        filtered_indices = recommendation_data.index.to_numpy()
        all_indices = np.append(filtered_indices, reference_index) if reference_index not in filtered_indices else filtered_indices


        similarity = similarity[all_indices, :]
        #recommendation_data = recommendation_data.append(chosen_restaurant_row)
        #
        chosen_restaurant_row = data.loc[[reference_index]]
        if reference_index not in filtered_indices:
             recommendation_data = pd.concat([recommendation_data, chosen_restaurant_row])

        recommendation_data.reset_index(inplace=True,drop=True)

    else:
        filtered_indices = data.index.to_numpy()
        all_indices = np.append(filtered_indices, reference_index) if reference_index not in filtered_indices else filtered_indices
        similarity = similarity[all_indices, :]
        recommendation_data = data
        recommendation_data.reset_index(inplace=True,drop=True)

    submit = st.sidebar.button("Show recommendations")

    if submit:
        if st.session_state['Option'] == 'Yes':
            indices = pd.Series(recommendation_data.index, index=recommendation_data['name']).drop_duplicates()
            result = restaurant_recommendation(restaurant,recommendation_data,indices,similarity)


        else:
            indices = pd.Series(data.index, index=data['name']).drop_duplicates()
            result = restaurant_recommendation(restaurant,recommendation_data,indices,similarity)



        result.reset_index(inplace=True, drop=True)
        st.session_state['Submitted'] = True
        st.session_state['result'] = result
        st.experimental_rerun()
def show_results():
    result = st.session_state['result']
    if len(result) < 1:
        st.info("Unfortunately, we couldn't find restaurants closely matching your preference this time. We apologize for the inconvenience. Please try selecting another restaurant for more tailored recommendations")
    else:
        result = result.drop(result.index[0])
        show_results = result[['name','Recommended','categories','rating','City','State','address','image_url']]

        new_column_names = {
                                'name': 'Restaurant Name',
                                'Recommended': 'Recommended,%',
                                'categories': 'Cuisine',
                                'rating': 'Avg Rating',
                                'City': 'City',
                                'State': 'State',
                                'address': 'Address',
                                'image_url': 'image_url'
                            }

        #st.dataframe(show_results)

        show_results.rename(columns=new_column_names, inplace=True)

        show_results = show_results[['image_url','Restaurant Name','Recommended,%','Cuisine','Avg Rating','City','State','Address']]
        st.data_editor(
                                show_results,
                                column_config={
                                "image_url": st.column_config.ImageColumn(
                                "", help="Streamlit app preview screenshots")
                                },
                                hide_index=True,
                                )
        #st.dataframe(show_results)

        col1,col2,col3 = st.columns([2,5,2])
        st.markdown(
            """
            <style>
            [data-baseweb="checkbox"] {
                margin-top: +35px;
            }
            </style>
            """,
            unsafe_allow_html=True)
        profile_select = col2.selectbox('',result['name'].unique().tolist(),index=None,help='Choose a restaurant to explore more about the restaurant such as location, reviews, ratings,etc.',placeholder="Select a restaurant for more information")

        if profile_select is not None:
              create_profile(profile_select)
def create_profile(profile_select):
    result = st.session_state['result']


    data = result[result['name']==profile_select]

    data.reset_index(drop=True,inplace=True)

    name = data['name'][0]
    url = data['url'][0]
    review_count = data['review_count'][0]

    if pd.isna(data['categories'][0]):
        phone = "Information not available"
    else:
        categories = data['categories'][0]
    rating = data['rating'][0]
    if pd.isna(data['display_phone'][0]):
        phone = "Information not available"
    else:
        phone = data['display_phone'][0]
    City = data['City'][0]
    State = data['State'][0]
    latitude = float(data['latitude'][0])
    longitude = float(data['longitude'][0])
    address = data['address'][0]
    similarity = data['Recommended'][0]
    info,review,recommendations,healthscore,website_link,span_texts,progress_ratings = scrape_restaurant_info(url)


    customer_reviews = find_dates_and_reviews(span_texts)


    cleaned_review = clean_and_split_review(review)
    business_hours = cleaned_review['business_hours']


    t1,t2,t3 = st.columns(3)
    t2.markdown('### '+name)



    #img2 = Image.open('noimage.jpeg')

    c1,c2,c3 = st.columns([2.5,2.5,2])
    #c1.image(img2)
    c1.markdown('##### Location')
    with c1.container():
        m = folium.Map(location=[latitude, longitude], zoom_start=18,dragging=False,zoom_control=False,
               scrollWheelZoom=False)
        folium.Marker(
            [latitude, longitude], popup=name, tooltip=name
        ).add_to(m)
        st_folium(m, width=400, height=300)

        route = f"http://maps.google.com/maps?z=12&t=m&q=loc:{latitude}+{longitude}"

        st.link_button('Get Directions',route)

    st.markdown(
        """
        <style>
        [data-testid="baseLinkButton-secondary"] {
            margin-left: 100px;
            margin-top: -40px;
        }
        </style>
        """,
        unsafe_allow_html=True)


    if 'Health Score' in healthscore:
        index = healthscore.index('Health Score')
        x = healthscore[index] +': ' +healthscore[index+1]
    else:
        x = 'Health Score: Information not available'

    url = data['url'][0]
    c2.markdown('##### General Information')
    c2.write('')
    c2.write('**Cuisine: '+ categories+'**')
    c2.write('**'+x+'**') #healthscore
    c2.write('**Avg Customer Rating: '+ str(rating)+'**')
    c2.write('**Total Reviews: '+ str(review_count)+'**')
    c2.write('**Phone Number: '+ str(phone)+'**')
    c2.write('**Place: '+ City + ', '+ State+'**')
    c2.write('**Address: '+ address+'**')
    c2.write('')


    if len(website_link) > 0:
        if len(website_link)>1:
            if name[:5] not in website_link[0]:
                link = str(website_link[1])
            else:
                link = str(website_link[0])
        else:
            link = str(website_link[0])
        if 'www' in link and 'https://' not in link:
            link = 'https://'+link
        elif 'https://' not in link and 'www.' not in link:
            link = 'https://www.'+link
        c2.link_button('View Website',link)
    else:
        c2.link_button('View Website',url)

    st.markdown(
    """
    <style>
        .stProgress > div > div{
            height: 65% 
        }
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to left, #f73d91 , #e3cad5);
        }
    </style>""",

    unsafe_allow_html=True)

    st.markdown(
    """
        <style>
        [data-baseweb="progress-bar"] {
            height: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True)

    c3.markdown('##### All Ratings')
    try:
        c3.write('')
        c3.progress(int(progress_ratings[0]), text='5 Star Ratings')
        c3.progress(int(progress_ratings[1]), text='4 Star Ratings')
        c3.progress(int(progress_ratings[2]), text='3 Star Ratings')
        c3.progress(int(progress_ratings[3]), text='2 Star Ratings')
        c3.progress(int(progress_ratings[4]), text='1 Star Ratings')
    except:
        st.info("No Information Available")

    with st.spinner('Whipping up something delicious, just a moment!'):
        with st.expander("Open Hours"):
            weekday = ['Monday: ','Tuesday: ','Wednesday: ','Thursday: ','Friday: ','Saturday: ','Sunday: ']
            loop = len(business_hours)
            if len(business_hours)>7:
                loop = 7
            for i in range(0,loop):
                formatted_hours = format_business_hours(business_hours[i])
                st.write(weekday[i] + formatted_hours)


        with st.expander("Additional Information"):
            try:
                if 'Health Score' in healthscore:
                    index = healthscore.index('Health Score')

                    filtered_data = [healthscore[index+2],healthscore[index+3],healthscore[index+4]]

                    grouped_data = [filtered_data[i:i+3] for i in range(0, len(filtered_data), 3)]

                    # Format as HTML with inline CSS
                    html_content = '<div style="display: flex; flex-wrap: wrap;">'
                    for group in grouped_data:
                        html_content += format_group(group)
                    html_content += '</div>'

                    # Display in Streamlit using HTML
                    st.markdown(html_content, unsafe_allow_html=True)
                elif 'Takes Reservations' in healthscore:
                    index = healthscore.index('Takes Reservations')

                    filtered_data = [healthscore[index],healthscore[index+1],healthscore[index+2],healthscore[index+3]]

                    grouped_data = [filtered_data[i:i+4] for i in range(0, len(filtered_data), 4)]

                    # Format as HTML with inline CSS
                    html_content = '<div style="display: flex; flex-wrap: wrap;">'
                    for group in grouped_data:
                        html_content += format_group(group)
                    html_content += '</div>'

                    # Display in Streamlit using HTML
                    st.markdown(html_content, unsafe_allow_html=True)
                elif 'Offers Delivery' in healthscore:
                    index = healthscore.index('Offers Delivery')

                    filtered_data = [healthscore[index],healthscore[index+1],healthscore[index+2],healthscore[index+3]]

                    grouped_data = [filtered_data[i:i+4] for i in range(0, len(filtered_data), 4)]

                    # Format as HTML with inline CSS
                    html_content = '<div style="display: flex; flex-wrap: wrap;">'
                    for group in grouped_data:
                        html_content += format_group(group)
                    html_content += '</div>'

                    # Display in Streamlit using HTML
                    st.markdown(html_content, unsafe_allow_html=True)
                else:
                    st.info("No Additional Information provided")
            except:
                st.info("No Additional Information provided")



        tab1, tab2, tab3 = st.tabs(["Popular dishes", "FAQ", "Reviews"])



        with tab1:
            try:
                items = split_and_clean_food_ideas(recommendations['popular_dishes'])
                if len(recommendations['dish_images']) > 1:
                    x = len(items)
                    img = image_select(
                        label="",
                        images= recommendations['dish_images'][:x],
                        captions=items[:x],use_container_width=False )
                else:
                    st.info('No data available')
            except:
                st.info('No data available')

        with tab2:
            if len(cleaned_review['faqs']) > 0:
                faq_list = clean_and_split_faq(cleaned_review['faqs'][0])
                for i in range(0,len(faq_list)):
                    st.markdown("**Q: "+ faq_list[i]['question']+"**")
                    st.write("**A:** "+ faq_list[i]['answer'].replace("$","\$"))
                    st.divider()
            else:
               st.info("No questions asked yet!")
        with tab3:
            if len(customer_reviews) > 0:
                dp = Image.open('dp.png')
                for date, review in customer_reviews.items():
                    st.image(dp,width=50)
                    st.markdown(f"**Reviewed On: {date}**<br>{review}", unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("No reviews available")

def app():
    img = Image.open('logo2.png')
    st.set_page_config(page_title='TasteMatch - Discover Your Next Favorite Restaurant',
                   layout = "wide",page_icon=img)
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            footer:after {
            content:'Developed by Sathish Prasad V T'; 
            visibility: visible;
            display: block;
            position: relative;
            #background-color: red;
            padding: 5px;
            top: 2px;
            }
            header {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    main()

    if 'Submitted' in st.session_state:
        show_results()

app()

#stars


