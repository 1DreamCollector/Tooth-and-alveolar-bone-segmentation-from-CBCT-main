This is a fully automatic AI system for tooth and alveolar bone segmentation from cone beam CT images (doi: https://doi.org/10.1038/s41467-022-29637-2 ）This article provides a complete reproduction version of tooth instance segmentation, which solves many problems and deficiencies in the original author's open source code, and adds its own modifications. During the original author's instance segmentation, although all teeth have independent instance labels that can be distinguished from other teeth, the predicted instance labels for each tooth are not fixed. It should be said that the labels come from the order in which the centroid of the original teeth is arranged on the x-axis. I made a small modification, and before making the changes, I processed the CT labels of the teeth. The voxel values of the labels for each position of the teeth are fixed. Let's take a look at the code for how to do it specifically, mainly the role played by multivariate cross entropy.



The result of tooth instance segmentation:

![1727060522822](C:\Users\17159\AppData\Roaming\Typora\typora-user-images\1727060522822.png)



![1727060562203](C:\Users\17159\AppData\Roaming\Typora\typora-user-images\1727060562203.png)