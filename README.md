# TasteMatch: Discover Your Next Favorite Restaurant

## Live Demo
Experience TasteMatch in action! Visit the [TasteMatch Streamlit App](https://tastematch.streamlit.app/) to see how our innovative solution transforms the way you discover and enjoy new restaurants.

## Project Overview
TasteMatch revolutionizes the dining discovery process with personalized restaurant recommendations. By analyzing vast amounts of user reviews using advanced NLP and Word2Vec models, TasteMatch caters to each user's unique culinary preferences, ensuring every dining experience is both delightful and personalized.

## Technology Used
- **Natural Language Processing (NLP)**: Employs NLP techniques to analyze restaurant reviews.
- **Word2Vec Models**: Converts review text into meaningful vector representations.
- **Python**: The backbone programming language for developing the NLP models and backend logic.
- **Streamlit**: Creates an engaging, interactive web application interface.
- **Pandas & NumPy**: Used for data handling and numerical calculations.
- **Gensim & NLTK**: Integral for model training and text processing in the NLP pipeline.
- **Docker**: Facilitates easy deployment and scaling of the application.

## Objectives
- **Customized Restaurant Recommendations**: Offer users tailored dining suggestions.
- **Utilizing User Review Data**: Leverage NLP for thorough analysis of user reviews for accurate recommendations.
- **User Experience Enhancement**: Develop an easy-to-use and engaging app interface for seamless restaurant discovery.

## Learning Outcomes
- **Applied NLP**: Gained real-world experience in the application of NLP and Word2Vec models.
- **Data Processing Expertise**: Enhanced skills in cleaning and preparing data for NLP.
- **Streamlit and Docker Proficiency**: Acquired experience in web app development and application containerization.

## Using Docker
To run TasteMatch using Docker, follow these steps:

1. **Install Docker**: Ensure Docker is installed on your system.

2. **Clone the Repository**:
   ```
   git clone https://github.com/yourusername/tastematch.git
   ```

3. **Build the Docker Image**:
   In the project directory, run:
   ```
   docker build -t tastematch
   ```

4. **Run the Container**:
   ```
   docker run -p 8501:8501 tastematch
   ```

Now, TasteMatch is up and running on your local machine!

---

*Note: Be sure to personalize the content and update links and details specific to your project before publishing the README.*
