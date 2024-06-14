<script setup>
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import InputText from 'primevue/inputtext';
import InlineMessage from 'primevue/inlinemessage';
import { useToast } from 'primevue/usetoast';
import { UserIcon, LockClosedIcon } from '@heroicons/vue/24/outline'

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
const _window = window
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      dialog_visible: false,
      message: "",
      email: "",
      password: "",
      password_confirm: "",
      password_confirm_mismatch: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("show_login_dialog", ({message}) => {
      this.dialog_visible = true
      this.message = message
    })
  },
  watch: {
    dialog_visible(new_value) {
      if (!new_value) {
        this.message = ""
      }
    }
  },
  methods: {
    login() {
      if (this.email === "" || this.password === "") {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter email and password' })
        return
      }
      this.$refs.login_form.submit()
    },
    register() {
      if (this.email === "" || this.password === "") {
        return
      }
      if (!this.email.includes("@")) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter a valid email' })
        return
      }
      if (this.password !== this.password_confirm) {
        this.password_confirm_mismatch = true
        return
      }
      this.$refs.register_form.submit()
    },
  },
}
</script>

<template>
  <div>
    <button
      v-if="!appState.logged_in"
      @click="dialog_visible = true"
      class="rounded p-2 text-sm text-gray-500 bg-gray-100 hover:bg-blue-100">
      Login / Register
    </button>

    <Dialog v-model:visible="dialog_visible" modal header="Login / Register">
      <p>{{ message }}</p>
      <Accordion :activeIndex="0" class="mb-2">
        <AccordionTab header="Login">
          <form ref="login_form" :action="`/org/login_from_app/?next=/`" method="post" class="flex flex-col gap-3">
            <InputGroup>
              <InputGroupAddon>
                <UserIcon class="h-4 w-4" />
              </InputGroupAddon>
              <InputText placeholder="E-Mail" v-model="email" name="email" />
            </InputGroup>

            <InputGroup>
              <InputGroupAddon>
                <LockClosedIcon class="h-4 w-4" />
              </InputGroupAddon>
              <InputText type="password" placeholder="Password" v-model="password" name="password" @keyup.enter="login" />
            </InputGroup>

            <Button label="Login" class="w-full" @click="login" />
          </form>
        </AccordionTab>
        <AccordionTab header="Register">
          <form ref="register_form" :action="`/org/signup_from_app/?next=/`" method="post" class="flex flex-col gap-3">
            <InputGroup>
              <InputGroupAddon>
                <UserIcon class="h-4 w-4" />
              </InputGroupAddon>
              <InputText placeholder="E-Mail" v-model="email" name="email" />
            </InputGroup>

            <InputGroup>
              <InputGroupAddon>
                <LockClosedIcon class="h-4 w-4" />
              </InputGroupAddon>
              <InputText type="password" placeholder="Password" v-model="password" name="password" />
            </InputGroup>

            <InputGroup>
              <InputGroupAddon>
                <LockClosedIcon class="h-4 w-4" />
              </InputGroupAddon>
              <InputText type="password" placeholder="Repeat Password" v-model="password_confirm" @keyup.enter="login"/>
              <InlineMessage v-if="password_confirm_mismatch">Passwords don't match</InlineMessage>
            </InputGroup>

            <Button label="Register" class="w-full" @click="register" />
          </form>
        </AccordionTab>
    </Accordion>
    </Dialog>
  </div>

</template>

<style scoped>
</style>../../stores/app_state_store../../stores/map_state_store
