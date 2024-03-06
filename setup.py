import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="virtaccl",
    version="0.0.0",
    author="SNS AP Team",
    author_email="zhukovap@ornl.gov",
    description="Package for running virtual SNS accelerator.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['pyepics',
                      'pcaspy',
                      'PyORBIT',
                      ],
    url="https://github.com/PyORBIT-Collaboration/virtual-accelerator",
    entry_points={
        "console_scripts": [
            "virtual_accelerator = virtaccl.virtual_accelerator:main",
        ]},

    packages=setuptools.find_packages(),

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    include_package_data=True,
)
