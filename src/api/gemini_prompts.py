# RJ Auto Metadata
# Copyright (C) 2025 Riiicil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# Semua konstanta prompt Gemini API

# --- KUALITAS (detail, versi lama) ---
PROMPT_TEXT = '''
Analyze the provided image and generate the following metadata strictly in English:

1.  Title: A unique, detailed and descriptive title for the image (minimum 6 words, maximum 160 characters). 
   - Make each title unique with specific details from the image
   - Focus on distinctive features, unusual aspects, or specific details
   - Include any unique lighting, composition, emotional tone, or context
   - Avoid generic descriptions that could apply to multiple similar images
   - Do not use any special characters or numbers in the title
   - Ensure the title is original and not repetitive
   - The title provides a clear and complete description of the image

2.  Description: A detailed description of the image content.
    - Minimum 6 words, maximum 160 characters
    - Use detailed, descriptive sentences or phrases to detail the Who, What, When, Where, and Why of your content.
    - Create a description that uniquely identifies your content
    - Include helpful details about angle, focus, etc
    - Avoid generic descriptions that could apply to multiple similar images
    - Do not merely list keywords as your description
    - Avoid repeating words or phrases
    - Do not include links, specific camera information, and trademarks (unless it is relevant for Editorial content only).
    - Maximum 160 characters!

3.  Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.  
    - Use specific and unique words (or compound words)
    - Stay between 60 and 65 keywords
    - Each keyword must be just ONE word 
    - Keywords should be related to the content of the image
    - DO NOT use multi-word phrases, only individual single words
    - Ensure keywords are relevant to the image content
    - Remember to include broader topics, feelings, concepts, or even associations
    - Do not enter unrelated terms or concepts
    - Do not repeat the same words or compound words
    - Do not include links, specific camera information, and trademarks (except for Editorial content)
    - All keywords are need to be relevant and encompass various aspects of the image and ways to find it

4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_PNG = '''
Analyze the provided image which has a transparent background and generate the following metadata strictly in English, focusing ONLY on the main subject(s):

1.  Title: A unique, detailed and descriptive title for the main subject(s) of the image (minimum 6 words, maximum 160 characters).
   - Describe only the visible subject(s), ignore the transparent background.
   - Make each title unique with specific details from the subject(s).
   - Focus on distinctive features, unusual aspects, or specific details of the subject(s).
   - Include any unique lighting, composition, emotional tone, or context related to the subject(s).
   - Avoid generic descriptions.
   - Do not use any special characters or numbers in the title.
   - Ensure the title is original and not repetitive.
   - The title provides a clear and complete description of the subject(s).

2.  Description: A detailed description of the main subject(s) of the image.
   - Minimum 6 words, maximum 160 characters.
   - Describe only the visible subject(s), ignore the transparent background.
   - Use detailed, descriptive sentences or phrases detailing the Who/What of the subject(s).
   - Create a description that uniquely identifies the subject(s).
   - Include helpful details about the subject's angle, focus, etc.
   - Avoid generic descriptions.
   - Do not merely list keywords as your description.
   - Avoid repeating words or phrases.
   - Do not include links, specific camera information, and trademarks (unless relevant for Editorial content).
   - Maximum 160 characters!

3.  Keywords: A list of SINGLE-WORD keywords only, related ONLY to the main subject(s), separated ONLY by commas.
   - Describe only the visible subject(s), ignore the transparent background.
   - Use specific and unique words (or compound words) describing the subject(s).
   - Stay between 60 and 65 keywords.
   - Each keyword must be just ONE word.
   - Keywords should be related to the subject(s) content.
   - DO NOT use multi-word phrases, only individual single words.
   - Ensure keywords are relevant to the subject(s) content.
   - Remember to include broader topics, feelings, concepts, or associations related to the subject(s).
   - Do not enter unrelated terms or concepts (especially background descriptions like 'isolated', 'white background', etc., unless the subject ITSELF is related to isolation).
   - Do not repeat the same words or compound words.
   - Do not include links, specific camera information, and trademarks (except for Editorial content).
   - All keywords need to be relevant and encompass various aspects of the subject(s) and ways to find it.

4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_VIDEO = '''
Analyze the provided multiple image frames from the same video and generate the following metadata strictly in English:

1. Title: A unique, detailed and descriptive title for the video (minimum 6 words, maximum 160 characters).
   - These images are multiple frames from the same video, analyze ALL frames to create a comprehensive title
   - Make each title unique with specific details from the visible content across all frames
   - Focus on distinctive features, unusual aspects, or specific details 
   - Include any unique visual elements, subjects, scene setting or context
   - Consider this is a video, not just static images
   - Observe motion, action, or scene changes between frames when available
   - Avoid generic descriptions that could apply to multiple similar videos
   - Do not use any special characters or numbers in the title
   - Ensure the title is original and not repetitive
   - The title should provide a clear and complete description of the video content

2. Description: A detailed description of the video content.
   - Minimum 6 words, maximum 160 characters
   - Analyze ALL provided frames collectively as they represent different moments of the same video
   - Describe the main subjects, actions, and setting visible across all frames
   - Look for indications of movement, progression, or action between frames
   - Include helpful details about what is happening in the video
   - Consider the dynamic nature of video content (action, movement, etc.)
   - Avoid generic descriptions that could apply to multiple similar videos
   - Do not merely list keywords as your description
   - Avoid repeating words or phrases
   - Do not include links, specific camera information, and trademarks (unless it is relevant for Editorial content only).
   - Maximum 160 characters!

3. Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.  
   - Use specific and unique words (or compound words)
   - Include keywords related to both static and dynamic video aspects
   - Stay between 60 and 65 keywords
   - Each keyword must be just ONE word 
   - Keywords should be related to the content of the video
   - DO NOT use multi-word phrases, only individual single words
   - Ensure keywords are relevant to the video content
   - Remember to include broader topics, feelings, concepts, or even associations
   - Include keywords related to video production, motion, action where appropriate
   - Do not enter unrelated terms or concepts
   - Do not repeat the same words or compound words
   - Do not include links, specific camera information, and trademarks (except for Editorial content)
   - All keywords need to be relevant and encompass various aspects of the video and ways to find it
 4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage
   
Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''


# --- SEIMBANG (dari draft_prompts.md) ---
PROMPT_TEXT_BALANCED = '''
Analyze the provided image and generate the following metadata strictly in English:

1. Title: A descriptive title for the image (minimum 6 words, maximum 160 characters).
   - Describe the main subject(s) and scene.
   - Avoid generic titles.

2. Description: A detailed description of the image content (minimum 6 words, maximum 160 characters).
   - Describe the main subjects and key actions/elements.
   - Avoid listing keywords as the description.

3. Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.
   - Provide relevant keywords covering the image content.
   - Ensure the list contains between 60 and 65 single-word keywords.

4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_PNG_BALANCED = '''
Analyze the provided image which has a transparent background and generate the following metadata strictly in English, focusing ONLY on the main subject(s):

1. Title: A descriptive title for the main subject(s) (minimum 6 words, maximum 160 characters).
   - Describe only the visible subject(s).
   - Avoid generic titles.

2. Description: A detailed description of the main subject(s) (minimum 6 words, maximum 160 characters).
   - Describe the main subject(s) and key details.
   - Avoid listing keywords as the description.

3. Keywords: A list of SINGLE-WORD keywords only, related ONLY to the main subject(s), separated ONLY by commas.
   - Provide relevant keywords covering the subject(s).
   - Avoid keywords related to the background (e.g., 'isolated', 'white background').
   - Ensure the list contains between 60 and 65 single-word keywords.

4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_VIDEO_BALANCED = '''
Analyze the provided multiple image frames from the same video and generate the following metadata strictly in English:

1. Title: A descriptive title for the video content (minimum 6 words, maximum 160 characters).
   - These images are multiple frames from the same video
   - Analyze ALL provided frames collectively to create a comprehensive title
   - Describe the main subjects, actions, and scene.
   - Consider this is part of a video (motion, action).
   - Look for changes or movement between frames
   - Avoid generic titles.

2. Description: A detailed description of the video content (minimum 6 words, maximum 160 characters).
   - Describe the main subjects, actions, and key elements across all provided frames.
   - Consider the dynamic nature of video content.
   - Look for progression or changes between frames
   - Avoid listing keywords as the description.

3. Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.
   - Provide relevant keywords covering the video content (static and dynamic aspects).
   - Ensure the list contains between 60 and 65 single-word keywords.

4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

# --- CEPAT (dari draft_prompts.md) ---
PROMPT_TEXT_FAST = '''
Analyze the provided image and generate the following metadata strictly in English:

1. Title: Generate a title (minimum 6 words, maximum 160 characters).
2. Description: Generate a description (minimum 6 words, maximum 160 characters).
3. Keywords: Generate 50 to 60 single-word keywords, separated by commas.
4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_PNG_FAST = '''
Analyze the provided image which has a transparent background and generate the following metadata strictly in English, focusing ONLY on the main subject(s):

1. Title: Generate a title for the main subject(s) (minimum 6 words, maximum 160 characters).
2. Description: Generate a description for the main subject(s) (minimum 6 words, maximum 160 characters).
3. Keywords: Generate 50 to 60 single-word keywords, separated by commas, related ONLY to the main subject(s).
4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
'''

PROMPT_TEXT_VIDEO_FAST = '''
Analyze the provided multiple image frames from the same video and generate the following metadata strictly in English:

1. Title: Generate a title for the video content (minimum 6 words, maximum 160 characters).
   - These images are multiple frames from the same video
   - Analyze ALL frames collectively to create a comprehensive title
   - Look for changes or movement between frames

2. Description: Generate a description for the video content (minimum 6 words, maximum 160 characters).
   - Consider all frames together to describe the video's content
   - Include observations about progression or changes between frames

3. Keywords: Generate 50 to 60 single-word keywords, separated by commas, covering the video content.
4.  Adobe Stock Category: Choose the single most relevant category for this image from the following list (write the number and name, e.g., "5. The Environment"):
     1. Animals
     2. Buildings and Architecture
     3. Business
     4. Drinks
     5. The Environment
     6. States of Mind
     7. Food
     8. Graphic Resources
     9. Hobbies and Leisure
     10. Industry
     11. Landscapes
     12. Lifestyle
     13. People
     14. Plants and Flowers
     15. Culture and Religion
     16. Science
     17. Social Issues
     18. Sports
     19. Technology
     20. Transport
     21. Travel

5.  Shutterstock Category: Choose the single most relevant category for this image from the following list (write the name exactly as shown):
     Abstract, Animals/Wildlife, Arts, Backgrounds/Textures, Beauty/Fashion, Buildings/Landmarks, Business/Finance, Celebrities, Education, Food and drink, Healthcare/Medical, Holidays, Industrial, Interiors, Miscellaneous, Nature, Objects, Parks/Outdoor, People, Religion, Science, Signs/Symbols, Sports/Recreation, Technology, Transportation, Vintage

Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
AdobeStockCategory: [number. name]
ShutterstockCategory: [name]
''' 