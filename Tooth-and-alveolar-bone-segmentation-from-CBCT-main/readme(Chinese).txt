这是A fully automatic AI system for tooth and alveolar bone segmentation from cone-beam CT images（doi:https://doi.org/10.1038/s41467-022-29637-2）这篇文章在牙齿实例分割上的完整复现版本，解决了原作者开源代码中存在的诸多问题和缺失，并添加了自己的修改，原作者实例分割时，虽然所有的牙齿都有能和其他牙齿区分开的独立的实例标签，但是每个牙齿的被预测的实例标签时不固定的，应该说标签是来自于原来的牙齿质心在x轴上排列的顺序。我加了一点小小的修改，再修改之前我把牙齿CT标签先处理了一下，每个位置的牙齿的标签体素值都是固定的。具体怎么做的看看代码吧，主要是多元交叉熵起到的作用。


牙齿实例分割的结果：

![Alt text](https://github.com/1DreamCollector/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/blob/main/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/pic/1.png)



![Alt text](https://github.com/1DreamCollector/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/blob/main/Tooth-and-alveolar-bone-segmentation-from-CBCT-main/pic/2.png)
