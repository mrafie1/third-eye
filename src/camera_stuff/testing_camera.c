#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include <camera/camera_api.h>

/*
 * Print the frame type we actually receive from the QNX camera driver.
 * This helps determine whether the driver is producing RGB8888 or another format.
 */

static volatile bool got_frame = false;


static void process_frame(
        camera_handle_t handle,
        camera_buffer_t *buffer,
        void *arg)
{
    (void)handle;
    (void)arg;

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

    got_frame = true;
}


int main(void)
{
    int err;
    camera_handle_t handle;
    camera_unit_t unit = CAMERA_UNIT_0;

    err = camera_open(unit, CAMERA_MODE_RO, &handle);

    if (err != CAMERA_EOK)
    {
        printf("camera_open failed %d\n", err);
        return 1;
    }

    err = camera_start_viewfinder(handle, process_frame, NULL, NULL);

    if (err != CAMERA_EOK)
    {
        printf("camera_start_viewfinder failed %d\n", err);
        camera_close(handle);
        return 1;
    }

    // Wait until one frame is inspected.
    while (!got_frame)
    {
        usleep(10000);
    }

    camera_stop_viewfinder(handle);
    camera_close(handle);

    return 0;
}
