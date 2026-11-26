#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>

int main(void) {
    int fd = open("/etc/hostname", O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }
    char buf[64];
    read(fd, buf, sizeof(buf));
    close(fd);
    return 0;
}
