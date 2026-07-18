#include <stdio.h>
#include <stdint.h>
#include <camera/camera_api.h>

/*
 * Print the frame type we actually receive from the QNX camera driver.
 * This helps determine whether the driver is producing RGB8888 or another format.
 */

void process_frame(camera_buffer_t *buffer)
{
    if (buffer == NULL)
    {
        printf("Error: NULL camera buffer\n");
        return;
    }

    // Always print the received format first
    printf("Received frame type: %d\n", buffer->frametype);

    switch (buffer->frametype)
    {
        case CAMERA_FRAMETYPE_RGB8888:
            printf("Format: RGB8888\n");

            {
                uint32_t width = buffer->framedesc.rgb8888.width;
                uint32_t height = buffer->framedesc.rgb8888.height;

                printf("Resolution: %ux%u\n", width, height);
            }

            break;

        default:
            printf("Unsupported frame format: %d\n", buffer->frametype);
            break;
    }
}