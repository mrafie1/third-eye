#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

#include <stdbool.h>
#include <unistd.h>
#include <camera/camera_api.h>

static volatile sig_atomic_t keep_running = 1;
static unsigned int frame_count = 0;

/*
 * Called when Ctrl+C is pressed.
 */
static void handle_signal(int signal_number)
{
    (void)signal_number;
    keep_running = 0;
}

void process_frame(camera_buffer_t *buffer)
{
    static unsigned int frame_count = 0;

    if (buffer == NULL)
    {
        fprintf(stderr, "Error: NULL camera buffer\n");
        return;
    }

    frame_count++;

    /*
     * Do not print every single frame or the terminal will be flooded.
     * Print the first frame and then every 30th frame.
     */
    if (frame_count != 1 && frame_count % 30 != 0)
    {
        return;
    }

    printf("\nFrame %u\n", frame_count);
    printf("Received frame type: %d\n", buffer->frametype);
    printf("Frame timestamp: %lld microseconds\n",
           (long long)buffer->frametimestamp);

    switch (buffer->frametype)
    {
        case CAMERA_FRAMETYPE_RGB8888:
        {
            uint32_t width = buffer->framedesc.rgb8888.width;
            uint32_t height = buffer->framedesc.rgb8888.height;

            printf("Format: RGB8888\n");
            printf("Resolution: %ux%u\n", width, height);
            printf("Pixel data address: %p\n", (void *)buffer->framebuf);
            break;
        }

        case CAMERA_FRAMETYPE_RGB888:
        {
            uint32_t width = buffer->framedesc.rgb888.width;
            uint32_t height = buffer->framedesc.rgb888.height;

            printf("Format: RGB888\n");
            printf("Resolution: %ux%u\n", width, height);
            break;
        }

        case CAMERA_FRAMETYPE_NV12:
        {
            uint32_t width = buffer->framedesc.nv12.width;
            uint32_t height = buffer->framedesc.nv12.height;

            printf("Format: NV12\n");
            printf("Resolution: %ux%u\n", width, height);
            break;
        }

        default:
            printf("Unsupported frame format: %d\n", buffer->frametype);
            break;
    }
}