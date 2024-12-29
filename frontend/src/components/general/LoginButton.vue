<script setup>
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import InputText from 'primevue/inputtext';
import InlineMessage from 'primevue/inlinemessage';
import Checkbox from 'primevue/checkbox';
import Message from 'primevue/message';
import { useToast } from 'primevue/usetoast';
import { UserIcon, LockClosedIcon } from '@heroicons/vue/24/outline'

import BorderButton from "../widgets/BorderButton.vue"

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
      terms_accepted: false,
      accordion_index: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("show_login_dialog", this.on_show_login_dialog)
    this.eventBus.on("show_register_dialog", this.on_show_register_dialog)
  },
  unmounted() {
    this.eventBus.off("show_login_dialog", this.on_show_login_dialog)
    this.eventBus.off("show_register_dialog", this.on_show_register_dialog)
  },
  watch: {
    dialog_visible(new_value) {
      if (!new_value) {
        this.message = ""
      }
    }
  },
  methods: {
    on_show_login_dialog({message}) {
      this.dialog_visible = true
      this.message = message
    },
    on_show_register_dialog({message}) {
      this.dialog_visible = true
      this.message = message
      this.accordion_index = 1
    },
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
      if (!this.terms_accepted) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please accept the terms of service and privacy policy' })
        return
      }
      this.$refs.register_form.submit()
    },
    continue_without_login() {
      if (!this.terms_accepted) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please accept the terms of service and privacy policy' })
        return
      }
      if (document.cookie.includes("anonymous_user_email")) {
        this.email = document.cookie.split('; ').find(row => row.startsWith('anonymous_user_email')).split('=')[1]
        this.password = document.cookie.split('; ').find(row => row.startsWith('anonymous_user_password')).split('=')[1]
      } else {
        const random_six_letter_id = Math.random().toString(36).substring(2, 8)
        this.email = `anonymous_user_${random_six_letter_id}`
        const random_password = Math.random().toString(36).substring(2, 8) + Math.random().toString(36).substring(2, 8)
        this.password = random_password
        // max-age is in seconds, 365 days = 365*24*60*60
        document.cookie = `anonymous_user_email=${this.email}; max-age=${365*24*60*60}; path=/`
        document.cookie = `anonymous_user_password=${this.password}; max-age=${365*24*60*60}; path=/`
      }
      this.$refs.register_form.submit()
    }
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

      <Message v-if="message">{{ message }}</Message>

      <Accordion :activeIndex="accordion_index" class="mb-2">
        <AccordionTab header="Login with an existing account">
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

        <AccordionTab header="Register / Create a new account">
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

            <div class="mt-3 mb-3 text-sm text-gray-500">
              <Checkbox v-model="terms_accepted" binary class="mr-2" />
              I agree to the
              <a href="https://absclust.com/terms-of-service" class="text-blue-500 hover:underline" target="_blank">Terms of Service</a>
              and
              <a href="https://absclust.com/privacy-policy" class="text-blue-500 hover:underline" target="_blank">Privacy Policy</a>.
            </div>

            <!-- put tooltip in div because it doesn't work when button is disabled otherwise -->
            <div v-tooltip.bottom="{ value: terms_accepted ? '' : 'You need to accept the terms of services and privacy policy to register.', showDelay: 400 }">
              <Button label="Register" class="w-full" @click="register" :disabled="!terms_accepted" />
            </div>
          </form>
        </AccordionTab>

        <AccordionTab header="Try without logging in">
          <div class="flex flex-col gap-3">

            <div class="text-gray-700">
              Only a limited set of features is available without logging in.<br>
              We recommend creating an account above, its free and just one step.
            </div>

            <div class="mt-3 mb-3 text-sm text-gray-500">
              <Checkbox v-model="terms_accepted" binary class="mr-2" />
              I agree to the
              <a href="https://absclust.com/terms-of-service" class="text-blue-500 hover:underline" target="_blank">Terms of Service</a>
              and
              <a href="https://absclust.com/privacy-policy" class="text-blue-500 hover:underline" target="_blank">Privacy Policy</a>.
            </div>

            <!-- put tooltip in div because it doesn't work when button is disabled otherwise -->
            <div v-tooltip.bottom="{ value: terms_accepted ? '' : 'You need to accept the terms of services and privacy policy to register.', showDelay: 400 }">
              <Button label="Continue without login" class="w-full" @click="continue_without_login" :disabled="!terms_accepted" />
            </div>
          </div>
        </AccordionTab>
    </Accordion>
    </Dialog>
  </div>

</template>

<style scoped>
</style>
