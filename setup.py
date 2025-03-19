from setuptools import setup, find_packages

setup(
    name="prompt-cli",  # Using prompt-cli since 'prompt' might be taken
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "prompt_toolkit",
        "pyperclip",
    ],
    entry_points={
        'console_scripts': [
            'prompt=prompt.main:cli',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A CLI tool for creating prompts with file references",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/prompt",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)