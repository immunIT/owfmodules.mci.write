# -*- coding: utf-8 -*-

# Octowire Framework
# Copyright (c) ImmunIT - Jordan Ovrè / Paul Duncan
# License: Apache 2.0
# Paul Duncan / Eresse <pduncan@immunit.ch>
# Jordan Ovrè / Ghecko <jovre@immunit.ch>

import os

from tqdm import tqdm

from octowire_framework.module.AModule import AModule
from octowire.mci import MCI
from owfmodules.mci.detect import Detect


class Write(AModule):
    def __init__(self, owf_config):
        super(Write, self).__init__(owf_config)
        self.meta.update({
            'name': 'MCI write',
            'version': '1.0.0',
            'description': 'Write data into Memory Card through MCI interface',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "start_address": {"Value": "", "Required": True, "Type": "hex",
                              "Description": "Address to start reading from.", "Default": 0x00},
            "data_file": {"Value": "", "Required": True, "Type": "file_r",
                          "Description": "The file containing the data to write on the Memory Card.", "Default": ""},
            "keep_existing": {"Value": "", "Required": True, "Type": "bool",
                              "Description": "Keep existing data if there is not enough data to fulfill a block."
                                             "Otherwise, it will erase the rest of the block (Write 0x00).",
                              "Default": True}
        }
        self.dependencies.extend([
            "octowire-lib>=1.0.6",
            "owfmodules.mci.detect>=1.0.0"
        ])

    def detect(self):
        detect_module = Detect(owf_config=self.config)
        detect_module.owf_serial = self.owf_serial
        resp = detect_module.run(return_value=True)
        if resp['status'] == 0:
            return resp["capacity"]
        else:
            self.logger.handle("Unable to retrieve the size of the Memory Card. Exiting...", self.logger.ERROR)
            return None

    def write(self):
        mci_interface = MCI(serial_instance=self.owf_serial)
        start_address = self.options["start_address"]["Value"]
        keep_existing = self.options["keep_existing"]["Value"]

        # Try to detect the MCI interface to retrieve the memory size.
        mc_size = self.detect() * 1024
        if mc_size is None:
            return

        # Check if the data size can fit in the Memory Card
        f_size = os.path.getsize(self.options["data_file"]["Value"])
        if f_size > mc_size or f_size > (mc_size - self.options["start_address"]["Value"]):
            self.logger.handle("The data size exceeds the Memory Cards size", self.logger.ERROR)

        # Write data
        self.logger.handle("Writing file's content into the Memory Card...", self.logger.INFO)
        with open(self.options["data_file"]["Value"], "rb") as f:
            progress_bar = tqdm(initial=0, total=f_size, desc="Writing", unit='B', unit_scale=True, ascii=" #",
                                bar_format="{desc} : {percentage:3.0f}%[{bar}] {n_fmt}/{total_fmt}B "
                                           "[elapsed: {elapsed} left: {remaining}, {rate_fmt}{postfix}]")
            while f_size > 0:
                # Write 8 block of 512 Bytes per iteration
                chunk = f.read(4096)
                mci_interface.transmit(data=chunk, start_addr=start_address, keep_existing=keep_existing)

                # Increment start address
                start_address = start_address + len(chunk)

                # Calculate remaining size
                f_size = f_size - len(chunk)

                # refresh the progress bar
                progress_bar.update(len(chunk))
                progress_bar.refresh()

            # Close the progress bar
            progress_bar.close()

    def run(self):
        """
        Main function.
        Write data into Memory Card through MCI interface.
        :return:
        """
        # If detect_octowire is True then detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. This sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return
        try:
            self.write()
        except ValueError as err:
            self.logger.handle(err, self.logger.ERROR)
        except Exception as err:
            self.logger.handle("{}: {}".format(type(err).__name__, err), self.logger.ERROR)