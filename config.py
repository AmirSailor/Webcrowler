EXCLUDE_TAGS = ['nav', 'script', 'style', 'header', 'footer', 'figure']
EXCLUDE_CLASSES = ['header__inner', 'social-share__title',
                    'social-share__items', 'content-group__title',
                      'content-group__body has-columns-4', 'footer f156hidz',
                        'footer__column footer__column--5', 'footer__column-content',
                          'logo logo--full footer__logo l979h8x', 'footer__details',
                            'footer__address', 'footer__copyright', 'footer__social',
                              'footer__social-link', 'footer__social-icon',
                                'footer__social-text', 'simple-menu__link', 'simple-menu__item',
                                'list simple-menu__list']
Project_name_c = input('Enter project name: \n')
Home_page_c = input('Enter project URL: \n')
Number_of_threads_c = input('Enter Number of Threads you can handle: \n')

# gemini-1.5-flash RPM
# Update if u have paid plan
Calls_1_Flash = 15
Period_1_Flash = 1500

# gemma-3-27b-it RPM
# Update if u have paid plan
Calls_27B_Gemma = 30
Period_27B_Gemma = 14400

Models_available = ['gemini-1.5-flash', 'gemma-3-27b-it']
Model = "gemma-3-27b-it"
# input('please enter one of these models gemma-3-27b-it or gemini-1.5-flash: \n')

Summery_Mode = False
# input('Do you want to Summarize the data? (True/False): \n')
