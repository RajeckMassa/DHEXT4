class Message:
    def __init__(self, inode, msg, data=None):
        self.data = data
        self.inode = inode
        self.msg = msg

    def __str__(self):
        return_message = "[INFO] Message: " + str(self.msg)
        if self.inode != -1:
            return_message = "[INFO] Inode: " + str(self.inode) + " Message: " + str(self.msg)
        if self.data is not None:
            return_message += " (A part of) the requested string " + self.data.decode() + " is found."
        return return_message
