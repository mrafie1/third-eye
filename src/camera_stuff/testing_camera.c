#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

#include <camera/camera_api.h>

static volatile sig_atomic_t keep_running = 1;
static volatile sig_atomic_t capture_finished = 0;
static const char *output_filename = "/tmp/third-eye.raw";

/*
 * Called when Ctrl+C is pressed.
 */
static void handle_signal(int signal_number)
{
    (void)signal_number;
    keep_running = 0;
}

/*
 * Inspect each frame received from the camera.
 */
static void process_frame(camera_buffer_t *buffer)
{
    FILE *output;
    uint32_t width;
    uint32_t height;
    uint32_t stride;

    if (buffer == NULL)
    {
        fprintf(stderr, "Error: NULL camera buffer\n");
        return;
    }

    if (capture_finished)
    {
        return;
    }

    if (buffer->frametype != CAMERA_FRAMETYPE_RGB8888)
    {
        fprintf(stderr, "Unsupported frame format: %d (RGB8888 required)\n",
                (int)buffer->frametype);
        capture_finished = -1;
        return;
    }

    width = buffer->framedesc.rgb8888.width;
    height = buffer->framedesc.rgb8888.height;
    stride = buffer->framedesc.rgb8888.stride;
    output = fopen(output_filename, "wb");
    if (output == NULL)
    {
        perror("Could not open capture output");
        capture_finished = -1;
        return;
    }

    /* Strip any QNX row padding from the saved RGB8888 frame. */
    for (uint32_t y = 0; y < height; y++)
    {
        size_t written = fwrite(
            buffer->framebuf + ((size_t)y * stride),
            1,
            (size_t)width * 4,
            output
        );
        if (written != (size_t)width * 4)
        {
            perror("Could not write complete camera frame");
            fclose(output);
            capture_finished = -1;
            return;
        }
    }

    if (fclose(output) != 0)
    {
        perror("Could not finish camera frame");
        capture_finished = -1;
        return;
    }

    /* Machine-readable output consumed by device_client.py. */
    printf("CAPTURE %u %u %s\n", width, height, output_filename);
    fflush(stdout);
    capture_finished = 1;
}

/*
 * QNX calls this whenever a new camera frame is available.
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
 * QNX calls this when the camera reports a status change.
 */
static void status_callback(
    camera_handle_t handle,
    camera_devstatus_t status,
    uint16_t extra,
    void *user_argument)
{
    (void)handle;
    (void)user_argument;

    printf(
        "Camera status event: status=%d, extra=%u\n",
        (int)status,
        (unsigned int)extra
    );

    fflush(stdout);
}

int main(int argc, char *argv[])
{
    camera_error_t error;
    camera_handle_t camera_handle = CAMERA_HANDLE_INVALID;

    camera_unit_t *camera_units = NULL;
    unsigned int camera_count = 0;
    camera_unit_t selected_camera;

    /*
     * Make Ctrl+C stop the program cleanly.
     */
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    if (argc > 2)
    {
        fprintf(stderr, "Usage: %s [output.raw]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (argc == 2)
    {
        output_filename = argv[1];
    }

    /*
     * First call: determine how many cameras are available.
     */
    error = camera_get_supported_cameras(
        0,
        &camera_count,
        NULL
    );

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_get_supported_cameras() failed: %d\n",
            (int)error
        );

        return EXIT_FAILURE;
    }

    if (camera_count == 0)
    {
        fprintf(stderr, "No supported cameras were found.\n");
        return EXIT_FAILURE;
    }

    printf("QNX found %u camera(s).\n", camera_count);

    /*
     * Allocate storage for the camera identifiers.
     */
    camera_units = calloc(
        camera_count,
        sizeof(*camera_units)
    );

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
        camera_units
    );

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "Could not retrieve the camera list: %d\n",
            (int)error
        );

        free(camera_units);
        return EXIT_FAILURE;
    }

    for (unsigned int i = 0; i < camera_count; i++)
    {
        printf(
            "Camera index %u has unit ID %d\n",
            i,
            (int)camera_units[i]
        );
    }

    /*
     * Use the first camera QNX reports.
     */
    selected_camera = camera_units[0];

    free(camera_units);
    camera_units = NULL;

    printf(
        "Opening camera unit %d...\n",
        (int)selected_camera
    );

    /*
     * Open the camera with read/write access.
     */
    error = camera_open(
        selected_camera,
        CAMERA_MODE_RW,
        &camera_handle
    );

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_open() failed: %d\n",
            (int)error
        );

        fprintf(
            stderr,
            "Close any other application currently using the camera.\n"
        );

        return EXIT_FAILURE;
    }

    printf("Camera opened successfully.\n");

    /*
     * The viewfinder mode must be set before starting it.
     */
    error = camera_set_vf_mode(
        camera_handle,
        CAMERA_VFMODE_VIDEO
    );

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_set_vf_mode() failed: %d\n",
            (int)error
        );

        camera_close(camera_handle);
        return EXIT_FAILURE;
    }

    /*
     * Start receiving camera frames through the callback.
     */
    error = camera_start_viewfinder(
        camera_handle,
        viewfinder_callback,
        status_callback,
        NULL
    );

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_start_viewfinder() failed: %d\n",
            (int)error
        );

        camera_close(camera_handle);
        return EXIT_FAILURE;
    }

    printf("Camera stream started; capturing one frame.\n");

    /*
     * Keep the main process alive while callbacks receive frames.
     */
    while (keep_running && capture_finished == 0)
    {
        sleep(1);
    }

    printf("Stopping camera stream...\n");

    error = camera_stop_viewfinder(camera_handle);

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_stop_viewfinder() failed: %d\n",
            (int)error
        );
    }

    error = camera_close(camera_handle);

    if (error != CAMERA_EOK)
    {
        fprintf(
            stderr,
            "camera_close() failed: %d\n",
            (int)error
        );

        return EXIT_FAILURE;
    }

    if (!keep_running || capture_finished < 0)
    {
        return EXIT_FAILURE;
    }

    printf("Camera closed successfully.\n");
    return EXIT_SUCCESS;
}
