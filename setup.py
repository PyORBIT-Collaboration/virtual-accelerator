import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    setup_requires=['setuptools_scm'],
    use_scm_version=True,

    name="virtaccl",
    dynamic=["version"],
    # version="0.0.0",
    author="SNS AP Team",
    author_email="catheybl@ornl.gov",
    description="Package for running virtual SNS accelerator.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['setuptools_scm',
                      'numpy',
                      'scipy',
                      'pyepics',
                      'pcaspy',
                      'PyORBIT',
                      ],
    url="https://github.com/PyORBIT-Collaboration/virtual-accelerator",
    entry_points={
        "console_scripts": [
            "sns_va = virtaccl.site.SNS_Linac.virtual_SNS_linac:main",
            "idmp_va = virtaccl.site.IDmp.IDmp_virtual_accelerator:main",
            "btf_va = virtaccl.site.btf.btf_virtual_accelerator:main",
        ]},

    packages=setuptools.find_packages(),

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    include_package_data=True,
    package_data={"": ["*.xml", "*.json", "*.dat"]},
)
