# Getting Started with Domino

This guide is intended to be a quickstart to get your model running on Domino and communicating with s3 and Moody's model service. Before getting started with domino, make sure you are familiar with the [model code](1_model_code.md) and [README](../README.md).

## Setting Up the Model in CAP

1. Navigate to the CAP Projects workspace and click **New Project**
![](media/Screenshot(5).png)
2. Give your project a name
![](media/Screenshot(6).png)
3. Navigate to **Files** and upload your project files. Alternatively, you could upload your files to GitHub and [link your GitHub project repo to Domino](#Linking-A-Git-Repository). This is the preferred way to manage files.
![](media/Screenshot(7).png)
![](media/Screenshot(8).png)
4. Navigate to **Settings** and choose an appropriate Docker image (Use Official CAP Image as default).
![](media/Screenshot(9).png)
5. That's it! Now its time to register your model with the [CAP Model Service](3_model_registry.md)

## Linking A Git Repository

Instead of manually uploading files to Domino, it is possible to have Domino pull your files from a git repository at runtime. This makes maintenance easier with respect to version control, but may have trade-offs when it comes to referencing a particular model version. At the time of this writing, Domino only integrates with GitHub. You will need to create a repo for your project on GitHub. In order for Domino to access your private repo on GitHub, you need to add your Git Credentials to your Domino account in **Account Settings/SSH Keys** in the UI.

1. Navigate to **Files > Git Repositories** and click **Add a New Repository**
![](media/Screenshot(13).png)
2. Add your GitHub URI, configure the branch/commit, and click **Add Repository**
![](media/Screenshot(16).png)

**NOTE:** It is highly recommended to use git tags to mamange versioning, and therefore as your git reference in this procedure

1. That's it! When Domino creates the container, it will pull your files from GitHub and run!

## Next up

You'll need to [register your model with the CAP Model Service](3_model_registry.md).