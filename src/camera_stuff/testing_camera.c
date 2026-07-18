#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

#include <camera/camera_api.h>

static volatile sig_atomic_t keep_running = 1;

/*
 * Called when Ctrl+C is pressed.
 */
static void handle_signal(int signal_number)
{
    (void)signal_number;
    keep_running = 0;
}

/*
 * Your original frame-processing function.
 */
static void process_frame(camera_buffer_t *buffer)
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

    fflush(stdout);
}

/*
 * This is the callback signature required by camera_start_viewfinder().
 *
 * QNX calls this automatically whenever a viewfinder frame arrives.
 */
static void viewfinder_callback(
    camera_handle_t handle,
    camera_buffer_t *buffer,
    void *user_argument)
{
    (void)handle;
    (void)user_argument;

    process_frame(buffer);
}

/*
 * This is called when the camera reports a status change.
 */
static void status_callback(
    camera_handle_t handle,
    camera_devstatus_t status,
    uint16_t extra,
    void *user_argument)
{
    (void)handle;
    (void)user_argument;

    printf("Camera status event: status=%d, extra=%u\n",
           (int)status,
           (unsigned int)extra);
    fflush(stdout);
}

int main(void)
{
    camera_error_t error;
    camera_handle_t camera_handle;
    camera_unit_t *camera_units = NULL;
    unsigned int camera_count = 0;
    camera_unit_t selected_camera;

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    /*
     * First call: ask QNX how many cameras are available.
     */
    error = camera_get_supported_cameras(
        0,
        &camera_count,
        NULL);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr,
                "camera_get_supported_cameras() failed: %d\n",
                error);
        return EXIT_FAILURE;
    }

    if (camera_count == 0)
    {
        fprintf(stderr, "No cameras were found by QNX.\n");
        return EXIT_FAILURE;
    }

    printf("QNX found %u camera(s).\n", camera_count);

    /*
     * Allocate enough space for the camera identifiers.
     */
    camera_units = calloc(camera_count, sizeof(*camera_units));

    if (camera_units == NULL)
    {
        perror("calloc");
        return EXIT_FAILURE;
    }

    /*
     * Second call: retrieve the actual camera identifiers.
     */
    error = camera_get_supported_cameras(
        camera_count,
        &camera_count,
        camera_units);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr,
                "Could not retrieve camera list: %d\n",
                error);
        free(camera_units);
        return EXIT_FAILURE;
    }

    for (unsigned int i = 0; i < camera_count; i++)
    {
        printf("Camera index %u has unit ID %d\n",
               i,
               (int)camera_units[i]);
    }

    /*
     * For this prototype, use the first available camera.
     */
    selected_camera = camera_units[0];
    free(camera_units);
    camera_units = NULL;

    printf("Opening camera unit %d...\n", (int)selected_camera);

    /*
     * Read/write access is necessary to start and stop the viewfinder.
     */
    error = camera_open(
        selected_camera,
        CAMERA_MODE_RW,
        &camera_handle);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr, "camera_open() failed: %d\n", error);
        fprintf(stderr,
                "Make sure another camera application is not running.\n");
        return EXIT_FAILURE;
    }

    printf("Camera opened successfully.\n");

    /*
     * Configure the camera for a stream of video/viewfinder frames.
     * Do this before setting other viewfinder properties.
     */
    error = camera_set_vf_mode(
        camera_handle,
        CAMERA_VFMODE_VIDEO);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr, "camera_set_vf_mode() failed: %d\n", error);
        camera_close(camera_handle);
        return EXIT_FAILURE;
    }

    /*
     * Register the frame and status callbacks, and begin streaming.
     */
    error = camera_start_viewfinder(
        camera_handle,
        viewfinder_callback,
        status_callback,
        NULL);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr,
                "camera_start_viewfinder() failed: %d\n",
                error);
        camera_close(camera_handle);
        return EXIT_FAILURE;
    }

    printf("Camera stream started.\n");
    printf("Press Ctrl+C to stop.\n");

    /*
     * The Camera API invokes the callbacks on separate threads.
     * The main thread must remain alive.
     */
    while (keep_running)
    {
        sleep(1);
    }

    printf("\nStopping camera stream...\n");

    error = camera_stop_viewfinder(camera_handle);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr,
                "camera_stop_viewfinder() failed: %d\n",
                error);
    }

    error = camera_close(camera_handle);

    if (error != CAMERA_EOK)
    {
        fprintf(stderr, "camera_close() failed: %d\n", error);
        return EXIT_FAILURE;
    }

    printf("Camera closed successfully.\n");
    return EXIT_SUCCESS;
}