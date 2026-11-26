#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>

int main(void) {
    int fd = open("/tmp/pcp-writer.out", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("open"); return 1; }
    if (write(fd, "hello-pcp\n", 10) != 10) { perror("write"); return 1; }
    close(fd);
    return 0;
}
