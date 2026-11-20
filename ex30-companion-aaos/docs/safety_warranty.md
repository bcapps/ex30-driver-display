# Display behavior

EX30 Driver Display is a supplementary instrument. Use the car’s native display for driving and warnings. The app reads Android Automotive vehicle properties. Each build runs `verifyReadOnly` over the Android source files.

The Pi clears missing fields on each complete snapshot and clears the screen readings when the active stream expires. Battery percentage and the power bar are derived readings. The source and limitations of each item are documented in the property catalog. [Vehicle signals](properties.md)
