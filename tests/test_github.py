from lum import github


# Test all possible links, non github links, non secured, etc.

test_list = [
    "https://github.com/far3x/lumen",         # normal link
    "http://github.com/far3x/lumen",          # non secured (http)
    "github.com/far3x/lumen",                 # no https no www
    "www.github.com/far3x/lumen",             # www only
    "https://www.github.com/far3x/lumen",     # https and www
    "https://youtube.com",                    # non github link
    "https://github.com/far3x/lumen.git"      # ends with .git
]

# Test if we can make links
for test in test_list:
    result = github.make_github_api_link(test)
    print(result)

print("\n\n")

# Test if we can send requests
for test in test_list:
    result = github.check_repo(test)
    print(result)